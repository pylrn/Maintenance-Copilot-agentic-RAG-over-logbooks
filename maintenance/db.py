"""Connection lifecycle, checked migrations, immutable corpus IO. Workflow SQL is P2-owned."""

import hashlib
import json
import re
from pathlib import Path

import asyncpg
import numpy as np
from pgvector.asyncpg import register_vector

from maintenance.contracts import CorpusManifest, ParsedCorpus, RecordSnapshot
from maintenance.ingest.manifest import truncation_annotations

ROOT = Path(__file__).resolve().parents[1]
IDENT_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_]*$"


class Database:
    def __init__(
        self,
        url,
        min_size=2,
        max_size=5,
        schema="public",
        vector_schema="public",
        ssl_root_cert=None,
        statement_cache_size=100,
    ):
        self.url = url
        self.min_size = min_size
        self.max_size = max_size
        s = schema or "public"
        vs = vector_schema or "public"
        if not re.fullmatch(IDENT_PATTERN, s):
            raise ValueError(f"invalid schema identifier: {schema}")
        if not re.fullmatch(IDENT_PATTERN, vs):
            raise ValueError(f"invalid vector schema identifier: {vector_schema}")
        self.schema = s
        self.vector_schema = vs
        self.ssl_root_cert = ssl_root_cert
        self.statement_cache_size = statement_cache_size
        self.pool = None

    async def open(self):
        schema = self.schema
        vector_schema = self.vector_schema

        async def setup(conn):
            for typ in ["json", "jsonb"]:
                await conn.set_type_codec(
                    typ, encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
                )
            if schema != "public":
                await conn.execute(
                    f"SET search_path = {schema}, {vector_schema}, pg_catalog"
                )
            vec_schema = await conn.fetchval(
                "SELECT nspname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE typname = 'vector' AND n.nspname = $1",
                vector_schema,
            )
            if not vec_schema:
                vec_schema = await conn.fetchval(
                    "SELECT nspname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE typname = 'vector' ORDER BY (nspname = 'extensions') DESC, nspname LIMIT 1"
                )
            if vec_schema:
                await register_vector(conn, schema=vec_schema)

        ssl_ctx = None
        if self.ssl_root_cert:
            import ssl

            cert_path = Path(self.ssl_root_cert)
            if not cert_path.exists():
                raise FileNotFoundError(f"Configured CA certificate not found: {self.ssl_root_cert}")
            ssl_ctx = ssl.create_default_context(cafile=str(cert_path))
            ssl_ctx.verify_mode = ssl.CERT_REQUIRED
            ssl_ctx.check_hostname = True

        server_settings = {}
        if schema != "public":
            server_settings["search_path"] = f"{schema},{vector_schema},pg_catalog"

        self.pool = await asyncpg.create_pool(
            self.url,
            min_size=self.min_size,
            max_size=self.max_size,
            init=setup,
            command_timeout=30,
            statement_cache_size=self.statement_cache_size,
            server_settings=server_settings if server_settings else None,
            ssl=ssl_ctx,
        )

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def migrate(self):
        applied = []
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock(710221)")
                await conn.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY, sha256 char(64) NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"
                )
                for path in sorted((ROOT / "db/migrations").glob("*.sql")):
                    text = path.read_text()
                    digest = hashlib.sha256(text.encode()).hexdigest()
                    old = await conn.fetchval(
                        "SELECT sha256 FROM schema_migrations WHERE name=$1", path.name
                    )
                    if old:
                        if old != digest:
                            raise ValueError(f"applied migration changed: {path.name}")
                        continue
                    await conn.execute(text)
                    await conn.execute(
                        "INSERT INTO schema_migrations(name,sha256) VALUES($1,$2)",
                        path.name,
                        digest,
                    )
                    applied.append(path.name)
        return applied

    async def ready(self):
        async with self.pool.acquire() as conn:
            actual = dict(await conn.fetch("SELECT name,sha256 FROM schema_migrations"))
        expected = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / "db/migrations").glob("*.sql")
        }
        return actual == expected

    async def ingest(self, corpus: ParsedCorpus):
        m = corpus.manifest
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock(710222)")
                old = await conn.fetchval(
                    "SELECT manifest FROM corpus_versions WHERE corpus_id=$1", m.corpus_id
                )
                if old:
                    if old != m.model_dump(mode="json"):
                        raise ValueError("corpus manifest mismatch")
                    count = await conn.fetchval(
                        "SELECT count(*) FROM maintenance_records WHERE corpus_id=$1", m.corpus_id
                    )
                    if count != m.record_count:
                        raise ValueError("incomplete existing corpus")
                    return False
                await conn.execute(
                    "INSERT INTO corpus_versions(corpus_id,domain,source_url,sha256,record_count,terms_note,manifest) VALUES($1,$2,$3,$4,$5,$6,$7)",
                    m.corpus_id,
                    m.domain,
                    m.source_url,
                    m.sha256,
                    m.record_count,
                    m.terms_note,
                    m.model_dump(mode="json"),
                )
                await conn.executemany(
                    "INSERT INTO maintenance_records(corpus_id,record_id,source_id,csv_row,original_fields,problem_raw,action_raw,problem_normalized,action_normalized,normalization_version,annotations,duplicate_key,source_model) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)",
                    [
                        (
                            r.corpus_id,
                            r.record_id,
                            r.source_id,
                            r.csv_row,
                            r.original_fields,
                            r.problem_raw,
                            r.action_raw,
                            r.problem_normalized,
                            r.action_normalized,
                            r.normalization_version,
                            {**r.annotations, "field_sha256": r.field_sha256},
                            r.duplicate_key,
                            r.source_model,
                        )
                        for r in corpus.records
                    ],
                )
        return True

    async def load_corpora(self, ids=None):
        async with self.pool.acquire() as conn:
            async with conn.transaction(isolation="repeatable_read", readonly=True):
                manifests = await conn.fetch(
                    "SELECT manifest FROM corpus_versions WHERE ($1::uuid[] IS NULL OR corpus_id=ANY($1)) ORDER BY domain,corpus_id",
                    ids,
                )
                result = []
                for item in manifests:
                    m = CorpusManifest.model_validate(item["manifest"])
                    rows = await conn.fetch(
                        "SELECT * FROM maintenance_records WHERE corpus_id=$1 ORDER BY csv_row",
                        m.corpus_id,
                    )
                    snapshots = []
                    for row in rows:
                        d = dict(row)
                        ann = dict(d["annotations"])
                        fields = ann.pop("field_sha256")
                        ann.update(
                            truncation_annotations(d["problem_raw"], d["action_raw"], m.domain)
                        )
                        snapshots.append(
                            RecordSnapshot(
                                **{k: v for k, v in d.items() if k != "annotations"},
                                domain=m.domain,
                                annotations=ann,
                                source_file_sha256=m.sha256,
                                field_sha256=fields,
                            )
                        )
                    result.append(ParsedCorpus(manifest=m, records=snapshots))
        return result

    async def store_vectors(self, corpus, representation, matrix, model, revision, text_hashes):
        from maintenance.retrieval.dense import normalized_matrix

        matrix = normalized_matrix(matrix, 384)
        if len(matrix) != len(corpus.records) or len(text_hashes) != len(matrix):
            raise ValueError("vector/source count mismatch")
        async with self.pool.acquire() as conn:
            vec_schema = await conn.fetchval(
                "SELECT nspname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE typname = 'vector' AND n.nspname = $1",
                self.vector_schema,
            )
            if not vec_schema:
                vec_schema = await conn.fetchval(
                    "SELECT nspname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE typname = 'vector' ORDER BY (nspname = 'extensions') DESC, nspname LIMIT 1"
                )
            if vec_schema:
                await register_vector(conn, schema=vec_schema)
            async with conn.transaction():
                # Advisory transaction lock for vector insertion atomicity
                await conn.execute("SELECT pg_advisory_xact_lock(710223)")
                # Check for existing vectors on full PK: (corpus_id, representation, embedding_model, model_revision)
                existing = await conn.fetch(
                    """
                    SELECT record_id, document_sha256, embedding
                    FROM record_embeddings
                    WHERE corpus_id = $1 AND representation = $2 AND embedding_model = $3 AND model_revision = $4
                    """,
                    corpus.manifest.corpus_id,
                    representation,
                    model,
                    revision,
                )
                if existing:
                    existing_map = {r["record_id"]: r for r in existing}
                    for r, v, h in zip(corpus.records, matrix, text_hashes, strict=True):
                        if r.record_id in existing_map:
                            old_row = existing_map[r.record_id]
                            if old_row["document_sha256"] != h:
                                raise ValueError(
                                    f"conflicting existing document hash for record {r.record_id}"
                                )
                            stored_vec = old_row["embedding"]
                            stored_arr = (
                                stored_vec.to_numpy()
                                if hasattr(stored_vec, "to_numpy")
                                else np.asarray(stored_vec, dtype=np.float32)
                            )
                            if not np.allclose(stored_arr, np.asarray(v, dtype=np.float32), atol=1e-5):
                                raise ValueError(
                                    f"conflicting existing embedding vector values for record {r.record_id}"
                                )

                await conn.executemany(
                    """
                    INSERT INTO record_embeddings(corpus_id, record_id, representation, embedding_model, model_revision, embedding, document_sha256)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (corpus_id, record_id, representation, embedding_model, model_revision) DO NOTHING
                    """,
                    [
                        (
                            r.corpus_id,
                            r.record_id,
                            representation,
                            model,
                            revision,
                            np.asarray(v),
                            h,
                        )
                        for r, v, h in zip(corpus.records, matrix, text_hashes, strict=True)
                    ],
                )
