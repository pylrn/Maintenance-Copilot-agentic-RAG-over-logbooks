"""Safe read-only database preflight check for local and managed PostgreSQL/Supabase."""

import argparse
import asyncio
import json
import os
import ssl

from dotenv import dotenv_values


def extract_target_info(url: str) -> dict[str, str]:
    try:
        from urllib.parse import urlsplit
        p = urlsplit(url)
        # Require valid postgresql scheme and nonempty hostname; otherwise return fixed redacted markers only
        if p.scheme not in ("postgresql", "postgres") or not p.hostname:
            return {
                "host": "redacted",
                "port": "redacted",
                "database": "redacted",
                "redacted_dsn": "postgresql://***:***@<redacted>",
            }
        host = p.hostname
        port = str(p.port) if p.port else "default"
        dbname = p.path.lstrip("/") if p.path else "unknown"
        if not dbname or " " in dbname or "=" in dbname:
            dbname = "unknown"
        scheme = p.scheme
        return {
            "host": host,
            "port": port,
            "database": dbname,
            "redacted_dsn": f"{scheme}://***:***@{host}:{port}/{dbname}",
        }
    except Exception:
        return {
            "host": "redacted",
            "port": "redacted",
            "database": "redacted",
            "redacted_dsn": "postgresql://***:***@<redacted>",
        }


async def run_preflight(env_file: str | None = None):
    vals = {}
    if env_file and os.path.exists(env_file):
        vals = dotenv_values(env_file)
    else:
        for fname in [".env", ".env.test", ".env.supabase"]:
            if os.path.exists(fname):
                vals.update(dotenv_values(fname))
        vals.update({k: v for k, v in os.environ.items() if k.startswith("DATABASE_")})

    url = vals.get("DATABASE_URL")
    if not url:
        return {"status": "error", "message": "DATABASE_URL not configured"}

    schema = vals.get("DATABASE_SCHEMA", "public")
    vector_schema = vals.get("VECTOR_SCHEMA", "public")
    cert_path = vals.get("DATABASE_SSL_ROOT_CERT")
    statement_cache_size = int(vals.get("STATEMENT_CACHE_SIZE", "0" if "supabase" in url else "100"))

    import asyncpg
    from pgvector.asyncpg import register_vector

    ssl_ctx = None
    ssl_verified = False
    if cert_path and os.path.exists(cert_path):
        ssl_ctx = ssl.create_default_context(cafile=cert_path)
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        ssl_ctx.check_hostname = True
        ssl_verified = True

    server_settings = {}
    if schema and schema != "public":
        server_settings["search_path"] = f"{schema},{vector_schema or 'extensions'},pg_catalog"

    target_info = extract_target_info(url)
    try:
        conn = await asyncpg.connect(
            url,
            ssl=ssl_ctx,
            statement_cache_size=statement_cache_size,
            server_settings=server_settings if server_settings else None,
            timeout=10,
        )
    except Exception as exc:
        return {
            "status": "connection_failed",
            "error_type": type(exc).__name__,
            "target_host": target_info["host"],
            "target_port": target_info["port"],
            "dsn": target_info["redacted_dsn"],
            "ssl_enabled": ssl_verified,
        }

    try:
        current_db = await conn.fetchval("SELECT current_database();")
        current_user = await conn.fetchval("SELECT current_user;")
        search_path = await conn.fetchval("SHOW search_path;")

        # Check migrations
        mig_table_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='schema_migrations' AND table_schema=$1);",
            schema if schema != "public" else "public",
        )
        migration_count = 0
        if mig_table_exists:
            migration_count = await conn.fetchval("SELECT count(*) FROM schema_migrations;")

        # Check vector extension
        vec_schema = await conn.fetchval(
            "SELECT nspname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE typname = 'vector' LIMIT 1;"
        )
        vector_registered = False
        if vec_schema:
            try:
                await register_vector(conn, schema=vec_schema)
                vector_registered = True
            except Exception:
                vector_registered = False

        # Check table count in targeted schema
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema=$1;",
            schema,
        )

        # Check corpus versions
        corpus_ids = []
        if any(t["table_name"] == "corpus_versions" for t in tables):
            rows = await conn.fetch("SELECT corpus_id, domain, record_count FROM corpus_versions;")
            corpus_ids = [
                {"corpus_id": str(r["corpus_id"]), "domain": r["domain"], "records": r["record_count"]}
                for r in rows
            ]

        return {
            "status": "ready" if mig_table_exists and vector_registered else "connected_uninitialized",
            "database": current_db,
            "user": current_user,
            "target_host": target_info["host"],
            "target_port": target_info["port"],
            "dsn": target_info["redacted_dsn"],
            "schema": schema,
            "search_path": search_path,
            "ssl_verified": ssl_verified,
            "migrations_count": migration_count,
            "vector_schema": vec_schema,
            "vector_registered": vector_registered,
            "table_count": len(tables),
            "corpora": corpus_ids,
        }
    finally:
        await conn.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Database preflight check")
    p.add_argument("--env-file", help="Path to environment file (e.g. .env, .env.supabase)")
    args = p.parse_args()
    report = asyncio.run(run_preflight(args.env_file))
    print(json.dumps(report, indent=2))
