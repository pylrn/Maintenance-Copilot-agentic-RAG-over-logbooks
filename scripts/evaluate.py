"""Frozen engineering retrieval checks. Does not claim agent/citation/refusal evaluation."""

import argparse
import asyncio
import hashlib
import json
import time
from pathlib import Path
from uuid import uuid4

import numpy as np

from maintenance.config import Settings
from maintenance.contracts import SearchSpec, ServiceScope
from maintenance.db import Database
from maintenance.models.embedding import BGEEncoder
from maintenance.retrieval.artifacts import load_bundle
from maintenance.retrieval.engine import RetrievalEngine

ROOT = Path(__file__).resolve().parents[1]


async def run(args):
    settings = Settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL required")
    file = Path(args.questions)
    questions = [json.loads(line) for line in file.read_text().splitlines() if line.strip()]
    frozen = json.loads((ROOT / "docs/p1/evaluation-freeze.json").read_text())["files"]
    if file.name in frozen and hashlib.sha256(file.read_bytes()).hexdigest() != frozen[file.name]:
        raise SystemExit("frozen query file changed")
    db = Database(settings.database_url.get_secret_value())
    await db.open()
    try:
        metadata = json.loads((settings.artifact_dir / "manifest.json").read_text())
        from uuid import UUID

        ids = list({UUID(e["corpus_id"]) for e in metadata["entries"]})
        corpora = await db.load_corpora(ids)
        encoder = BGEEncoder(
            settings.embedding_revision, settings.model_cache_dir, settings.embedding_query_prefix
        )
        matrices, _ = load_bundle(settings.artifact_dir, corpora, encoder)
        scope = ServiceScope(owner_id=uuid4(), corpus_ids=ids)
        configurations = [
            ("raw_bm25", ["bm25_raw"], False),
            ("dense_only", ["dense"], False),
            ("hybrid_rrf", ["bm25_raw", "bm25_normalized", "dense"], False),
            ("hybrid_compatibility", ["bm25_raw", "bm25_normalized", "dense"], True),
        ]
        result = {
            "question_file": str(file),
            "query_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
            "label_status": "provisional engineering labels, human review pending; broader relevant cases may be unlabeled",
            "model": metadata["model"],
            "corpora": [c.manifest.model_dump(mode="json") for c in corpora],
            "configurations": [],
            "agent_metrics": {
                "citation_precision": None,
                "correct_refusal": None,
                "false_refusal": None,
                "tokens": None,
                "reason": "Person two agent/evidence gate/provider not integrated.",
            },
        }
        for name, channels, compat in configurations:
            engine = RetrievalEngine(
                corpora, matrices, encoder, channels=channels, use_compatibility=compat
            )
            timings = []
            details = []
            hits = 0
            for q in questions:
                start = time.perf_counter()
                sr = await engine.search(
                    SearchSpec(query_raw=q["query"], domain=q["domain"], top_k=5), scope
                )
                elapsed = (time.perf_counter() - start) * 1000
                timings.append(elapsed)
                acceptable = {rid for rid, grade in q["relevance"].items() if grade == 2}
                # A visible representative carries its exact duplicate source IDs.
                found = any(acceptable & set(h.duplicate_ids) for h in sr.hits)
                hits += int(found)
                details.append(
                    {
                        "query_id": q["query_id"],
                        "hit": found,
                        "top5": [h.record_id for h in sr.hits],
                        "elapsed_ms": round(elapsed, 2),
                    }
                )
            result["configurations"].append(
                {
                    "name": name,
                    "hit_at_5": hits,
                    "positive_questions": len(questions),
                    "p50_ms": round(float(np.percentile(timings, 50)), 2),
                    "p95_ms": round(float(np.percentile(timings, 95)), 2),
                    "details": details,
                }
            )
        output = ROOT / "docs/p1/retrieval-evaluation.json"
        output.write_text(json.dumps(result, indent=2))
        lines = [
            "# Retrieval evaluation",
            "",
            f"Source: `{file.name}`; {len(questions)} frozen pre-run engineering questions. Labels are provisional, limited to exact original PROBLEM groups, and need human review. This is not organizer gold data.",
            "",
            "Duplicate-aware Hit@5 counts a representative if its exact duplicate members include a labeled record. No thresholds were tuned on this run. All source records remain searchable. Timings are local CPU query timings with model/index preloaded; first-call effects are included.",
            "",
            "| Configuration | Hit@5 | p50 ms | p95 ms |",
            "|---|---:|---:|---:|",
        ]
        for r in result["configurations"]:
            lines.append(
                f"| {r['name']} | {r['hit_at_5']}/{r['positive_questions']} | {r['p50_ms']} | {r['p95_ms']} |"
            )
        lines += [
            "",
            "Agent citation precision, refusal rates, tokens, public hosting latency, optional reranker and UI behavior were not measured. Person two must complete those integration checks. Dense-only/raw BM25 versus hybrid results are engineering observations on this small label set, not a claim that one configuration always wins.",
            "",
            f"Model: `{encoder.model_id}` at `{encoder.revision}`, normalized 384-dimensional vectors with the recorded BGE query prefix.",
        ]
        (ROOT / "docs/p1/retrieval-evaluation.md").write_text("\n".join(lines) + "\n")
        print(
            json.dumps(
                {
                    "configurations": [
                        {k: v for k, v in r.items() if k != "details"}
                        for r in result["configurations"]
                    ],
                    "report": str(output),
                },
                indent=2,
            )
        )
    finally:
        await db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--questions", default="eval/heldout.jsonl")
    asyncio.run(run(p.parse_args()))
