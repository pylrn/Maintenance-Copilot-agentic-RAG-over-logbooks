"""Connection lifecycle, checked migrations, immutable corpus IO. Workflow SQL is P2-owned."""

import hashlib
import json
from pathlib import Path

import asyncpg
import numpy as np
from pgvector.asyncpg import register_vector

from maintenance.contracts import CorpusManifest, ParsedCorpus, RecordSnapshot
from maintenance.ingest.manifest import truncation_annotations

ROOT = Path(__file__).resolve().parents[1]


class Database:
    def __init__(self, url, min_size=2, max_size=5):
        self.url = url
        self.min_size = min_size
        self.max_size = max_size
        self.pool = None

    async def open(self):
        async def setup(conn):
            for typ in ["json", "jsonb"]:
                await conn.set_type_codec(
                    typ, encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
                )
            if await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_type WHERE typname='vector')"):
                await register_vector(conn)

        self.pool = await asyncpg.create_pool(
            self.url, min_size=self.min_size, max_size=self.max_size, init=setup, command_timeout=30
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
            await register_vector(conn)
            async with conn.transaction():
                await conn.executemany(
                    "INSERT INTO record_embeddings(corpus_id,record_id,representation,embedding_model,model_revision,embedding,document_sha256) VALUES($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING",
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
