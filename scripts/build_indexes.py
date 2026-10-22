import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from maintenance.config import Settings
from maintenance.db import Database
from maintenance.models.embedding import BGEEncoder
from maintenance.retrieval.artifacts import load_bundle, save_bundle


async def run(args):
    settings = Settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL required")
    revision = settings.embedding_revision
    if args.download:
        from huggingface_hub import model_info

        revision = revision or model_info(settings.embedding_model).sha
    encoder = BGEEncoder(
        revision,
        settings.model_cache_dir,
        settings.embedding_query_prefix,
        local_only=not args.download,
    )
    db = Database(
        settings.database_url.get_secret_value(),
        schema=settings.database_schema,
        vector_schema=settings.vector_schema,
        ssl_root_cert=settings.database_ssl_root_cert,
        statement_cache_size=settings.statement_cache_size,
    )
    await db.open()
    try:
        corpora = await db.load_corpora(
            [UUID(x) for x in args.corpus_id] if args.corpus_id else None
        )
        if not corpora:
            raise SystemExit("import corpora before building indexes")
        domains = [c.manifest.domain for c in corpora]
        if len(set(domains)) != len(domains):
            raise SystemExit("select one active corpus per domain using --corpus-id")
        meta, publish_manifest = await asyncio.to_thread(
            save_bundle, settings.artifact_dir, corpora, encoder, False
        )
        matrices, _ = load_bundle(settings.artifact_dir, corpora, encoder, meta=meta)
        for c in corpora:
            for representation in ["problem", "problem_action"]:
                e = next(
                    e
                    for e in meta["entries"]
                    if e["corpus_id"] == str(c.manifest.corpus_id)
                    and e["representation"] == representation
                )
                key = str(c.manifest.corpus_id) + (
                    ":problem_action" if representation == "problem_action" else ""
                )
                await db.store_vectors(
                    c,
                    representation,
                    matrices[key],
                    encoder.model_id,
                    revision,
                    e["document_hashes"],
                )
        # Publish active manifest and model pin ONLY after all database vectors succeed
        await asyncio.to_thread(publish_manifest)
        (Path(settings.artifact_dir) / "model-pin.json").write_text(
            json.dumps(meta["model"], indent=2)
        )
        print(
            json.dumps(
                {
                    "model": meta["model"],
                    "corpora": [str(c.manifest.corpus_id) for c in corpora],
                    "representations": ["problem", "problem_action"],
                    "database_vectors_persisted": True,
                }
            )
        )
    finally:
        await db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--download", action="store_true")
    p.add_argument("--corpus-id", action="append")
    asyncio.run(run(p.parse_args()))
