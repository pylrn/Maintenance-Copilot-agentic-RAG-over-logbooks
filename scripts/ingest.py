import argparse
import asyncio
import json
from pathlib import Path

from maintenance.config import Settings
from maintenance.db import Database
from maintenance.ingest.aviation import parse_aviation
from maintenance.ingest.facility import parse_facility


async def run(args):
    settings = Settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL required")
    db = Database(
        settings.database_url.get_secret_value(),
        schema=settings.database_schema,
        vector_schema=settings.vector_schema,
        ssl_root_cert=settings.database_ssl_root_cert,
        statement_cache_size=settings.statement_cache_size,
    )
    await db.open()
    try:
        if args.migrate:
            print(json.dumps({"applied_migrations": await db.migrate()}))
        if args.source:
            if not args.domain:
                raise SystemExit("--domain required with --source")
            parse = parse_aviation if args.domain == "aviation" else parse_facility
            c = parse(Path(args.source).read_bytes(), args.expected_sha256)
            created = await db.ingest(c)
            out = settings.artifact_dir / "corpora"
            out.mkdir(parents=True, exist_ok=True)
            manifest_file = out / f"{c.manifest.corpus_id}.json"
            if not manifest_file.exists():
                manifest_file.write_text(c.manifest.model_dump_json(indent=2))
            print(json.dumps({"created": created, "manifest": c.manifest.model_dump(mode="json")}))
    finally:
        await db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--migrate", action="store_true")
    p.add_argument("--source")
    p.add_argument("--domain", choices=["aviation", "facility"])
    p.add_argument("--expected-sha256")
    asyncio.run(run(p.parse_args()))
