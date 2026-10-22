# Retrieval Lab Implementation Progress

**Branch:** `gdd/retrieval-lab`
**Base:** `1e131c2`
**Target:** `/Volumes/MAC/Projects_devolopment/nexai_gdd_retrieval_lab`

## Task Checklist & Status

- [x] **Phase 1: Exploration & System Understanding**
  - [x] Create initial progress tracking doc (`docs/retrieval-lab/PROGRESS.md`)
  - [x] Inspect existing `RetrievalEngine`, `api/main.py`, search routes, auth checks, and data contracts
  - [x] Verify test suite baseline (`PYTHONPATH=. .venv/bin/pytest -q`) and linter (`ruff check api maintenance scripts tests`)
- [x] **Phase 2: Shared RetrievalEngine Instrumentation (Trace Truthfulness)**
  - [x] Trace all actual applicable stages: queue, normalization, embedding, raw BM25, normalized BM25, dense cosine, fusion, compatibility/filtering, dedup, optional rerank, top_k_selection, record fetch
  - [x] Add typed optional trace fields to `SearchResult` / response without breaking existing contracts or adding fake timings/separate fake pipelines
  - [x] Attach full source snapshot to each `SearchHit` for instant exact field / SHA256 inspection
  - [x] Bounded trace payload, no secrets or prompts, no DB growth
- [x] **Phase 3: Lab API Endpoints (`/api/maintenance/v1/lab`)**
  - [x] Records inspection endpoint (`GET /api/maintenance/v1/lab/records`) with pagination, filtering, canonical mentions (e.g. cylinder), domain selection, real source fields and hashes, facility action null handling, 404 on invalid corpus
  - [x] Storage inspection endpoint (`GET /api/maintenance/v1/lab/storage`) with dynamic DB/table sizes, counts, index counts, timestamp, quota 500,000,000 bytes with Free plan database quota (configured 500MB), no invented capacity, truth-revealing status on DB disconnect
  - [x] Projection inspection endpoint (`GET /api/maintenance/v1/lab/projection`) with centered PCA2 (deterministic numpy SVD/eigh), method, explained variance, model revision, source hash, cached in memory per immutable engine (bounded 6 entries), max_points sliced on response, async to_thread+lock
  - [x] Auth & origin security checks matching existing owner/origin standards
- [x] **Phase 4: Retrieval Lab Web UI (`/retrieval-lab`)**
  - [x] Static HTML/CSS/JS UI served at `/retrieval-lab`
  - [x] Query form: domain, fault vs action_history, topk, duplicate collapse, quality rerank, component/symptom filters
  - [x] Tracing & diagnostic displays: original/normalized query, mentions, measured stage timings and counts, per-hit channel ranks, scores, RRF, compatibility, duplicate members, revisions, degraded branches
  - [x] Raw SearchResult JSON & Telemetry section with instant Copy & Download JSON buttons
  - [x] Record detail drawer/modal: shared async source fetch guarded against race conditions, exact source fields, SHA256 hashes
  - [x] 2D PCA projection scatter visualization (all points plotted without sampling, query hit highlights, domain filter on points + highlights + picker, point selection to raw record)
  - [x] Storage & system stats display tab/card with truthful null handling and dense vector memory metrics
  - [x] Main maintenance UI (`/maintenance`) stays completely untouched
- [x] **Phase 5: Verification & Quality Assurance**
  - [x] Unit & integration tests for endpoint-agent parity, trace accuracy, pagination/filtering, projection determinism/provenance, facility null action, auth/origin refusal, cache isolation, DB error storage fallback (81 passed)
  - [x] Full pytest and ruff validation
  - [x] Generate comprehensive `docs/retrieval-lab/REPORT.md`
  - [x] Local git commit
