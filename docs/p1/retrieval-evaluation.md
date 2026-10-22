# Retrieval evaluation

Source: `heldout.jsonl`; 15 frozen pre-run engineering questions. Labels are provisional, limited to exact original PROBLEM groups, and need human review. This is not organizer gold data.

Duplicate-aware Hit@5 counts a representative if its exact duplicate members include a labeled record. No thresholds were tuned on this run. All source records remain searchable. Timings are local CPU query timings with model/index preloaded; first-call effects are included.

| Configuration | Hit@5 | p50 ms | p95 ms |
|---|---:|---:|---:|
| raw_bm25 | 11/15 | 381.26 | 468.32 |
| dense_only | 12/15 | 419.38 | 1259.24 |
| hybrid_rrf | 12/15 | 424.22 | 461.26 |
| hybrid_compatibility | 12/15 | 412.92 | 514.64 |

Agent citation precision, refusal rates, tokens, public hosting latency, optional reranker and UI behavior were not measured. Person two must complete those integration checks. Dense-only/raw BM25 versus hybrid results are engineering observations on this small label set, not a claim that one configuration always wins.

Model: `BAAI/bge-small-en-v1.5` at `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, normalized 384-dimensional vectors with the recorded BGE query prefix.
