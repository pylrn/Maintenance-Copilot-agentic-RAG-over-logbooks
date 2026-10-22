# Development log

## 22 October 2026 — person one

- Initialized `person-1-retrieval-platform` in the user-requested volume folder; copied existing plan, owner briefs, screenshot, prompt and immutable 44-file reference snapshot.
- Wrote regression tests before ingestion/search/contracts/API behavior. Added real PostgreSQL tests with a separate database. Fixed the facility's explicit midnight format and distinguished typed engine versus cylinder number contexts.
- Created shared maintenance/v1 contracts and clearly marked synthetic fixtures. P2 review remains pending.
- Ingested original aviation/facility snapshots with checksums and raw preservation. Built normalized 384-dimensional BGE vectors at immutable revision 5c38ec7c405ec4b44b94cc5a9bb96e735b38267a, both representations, with source/order/hash manifests and pgvector persistence.
- Implemented true BM25, exact dense cosine, RRF, conservative compatibility tiers and duplicate groups; deterministic comparison/count/sensitivity receipts; source-version lookup; identity/origin controls and readiness API composition.
- Froze 15 provisional positive engineering questions before first real-model evaluation. Raw BM25 Hit@5 11/15, dense-only 12/15, hybrid 12/15. No threshold tuning or agent accuracy claim. Human relevance-label review remains pending.
- Created Docker/Compose, resolved locks, runbook and P2 handoff. Linux dependency resolution explicitly selects CPU PyTorch to avoid unused CUDA libraries.
- Agent, evidence gate, durable workflow implementation, adapted UI, live DeepSeek test and public deployment remain integration work; no missing capability is represented as implemented.
- Final native suite: 33 passed with a separate PostgreSQL test database; lint and source compilation passed. CPU Docker image built, non-root runtime verified, package compatibility check passed, and real aviation/facility/source endpoints passed from the container. The running backend is at http://localhost:8000; workflow/UI readiness remains false.

## GitHub repository alignment

User designated `pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks` as the destination for all commits. Connected origin, incorporated its existing main history without dropping test.py/test1.py, and retained person-one ownership on its development branch. Main is not merged automatically.
