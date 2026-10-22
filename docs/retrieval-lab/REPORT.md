# Retrieval Testing Workbench Implementation Report

**Repository Target:** `/Volumes/MAC/Projects_devolopment/nexai_gdd_retrieval_lab`
**Branch:** `gdd/retrieval-lab`
**Base Commit:** `1e131c2`
**Local Port:** 8102 (configured in `.env`)
**UI Route:** `GET /retrieval-lab`
**API Prefix:** `/api/maintenance/v1`

---

## 1. Summary of Outcome

A complete local retrieval testing workbench has been implemented in `/Volumes/MAC/Projects_devolopment/nexai_gdd_retrieval_lab`. The workbench shares the identical retrieval pipeline used by the agent tool `tool_search_records` and `POST /api/maintenance/v1/search`, providing full stage timing and count diagnostics, candidate-level channel inspection, provenance verification, dynamic storage monitoring, and a deterministic 2D PCA corpus projection without sampling.

The main production maintenance interface (`/maintenance`) remains completely unchanged.

---

## 2. Changed & Created Files

| File | Status | Description |
|---|---|---|
| `maintenance/contracts.py` | Modified | Added typed optional `trace: SearchTrace \| None` on `SearchResult` and `record_snapshot: RecordSnapshot \| None` on `SearchHit`. Preserved existing schema validation and backward compatibility. |
| `maintenance/retrieval/engine.py` | Modified | Instrumented `RetrievalEngine.search` and `_retrieve` with truthful measured timings and counts across all 12 stages. Precomputed source mentions/components/symptoms at startup to reduce repeated annotation work. Added explicit conservative cylinder membership from `cylinder_number` / normalized tokens in source component cache. Attached deep snapshot copies to hits. Removed duplicate dead code. Added projection cache and query embedding cache per engine instance. |
| `api/main.py` | Modified | Registered `/api/maintenance/v1/lab` router and served `/retrieval-lab` static UI without altering `/maintenance`. Added single-token query encoder warmup on startup to prevent cold-start latency. Added `no-store` cache control headers to prevent asset mixing. |
| `api/routes/lab.py` | Created | Bounded authenticated inspection endpoints: `GET /lab/records` (pagination, filtering, canonical mentions), `GET /lab/storage` (database and table sizes, quota, index memory), `GET /lab/projection` (deterministic centered PCA2 over real matrices, cached in memory per engine instance). |
| `api/static/retrieval_lab.html` | Created | Light Hybrid Search Admin UI with persistent left sidebar, latency timing banner, active filter badges, light result cards, collapsible 12-stage diagnostics waterfall, raw JSON telemetry, 2D PCA Projection scatter, Corpus Records Browser, Storage/Quota monitor, and Record Detail Modal. |
| `api/static/retrieval_lab.css` | Created | Light stylesheet for the Hybrid Search Admin workbench (tokens matching modern clean admin UI with tier pills, score pills, evidence box, and feedback controls). |
| `api/static/retrieval_lab.js` | Created | Workbench client logic: persistent query runner, timing banner calculations (client HTTP, server total, embedding, recall/compat, rerank), result cards with "Why ranked here?" facts grid, evidence backing with verbatim quotes and Unicode codepoint offsets, WebCrypto SHA256 verification of raw source fields against uppercase recorded hashes, human feedback export, canvas scatter plot with pan/zoom/query hit highlights/domain-filtered picking, paginated record browser, and race-condition-guarded async record detail fetch. |
| `tests/integration/test_lab.py` | Created | Integration tests covering search endpoint-agent parity, trace accuracy across 12 stages, pagination/filtering, deterministic PCA projection, facility null actions, auth/origin refusal, projection cache isolation, DB error handling, and canonical mentions filtering for both records and search. |
| `tests/ui/test_ui.py` | Modified | Added UI tests for `/retrieval-lab` HTML and static assets. |
| `docs/retrieval-lab/PROGRESS.md` | Created | Tracked progress across all implementation phases. |
| `docs/retrieval-lab/REPORT.md` | Created | Comprehensive final report. |

---

## 3. Exact Verification Checks & Results

### 3.1 Test Suite Verification
Command:
```bash
cd /Volumes/MAC/Projects_devolopment/nexai_gdd_retrieval_lab
PYTHONPATH=. .venv/bin/pytest -q
```
Output:
```
................................................................................. [100%]
81 passed in 2.25s
```
All 81 tests pass (70 baseline tests + 11 new comprehensive integration and UI tests).

### 3.2 Linter Verification
Command:
```bash
cd /Volumes/MAC/Projects_devolopment/nexai_gdd_retrieval_lab
.venv/bin/ruff check api maintenance scripts tests
```
Output:
```
All checks passed!
```

### 3.3 Key Verification Areas Tested
1. **Search Endpoint - Agent Tool Parity (`test_search_endpoint_and_agent_tool_parity`):**
   - Confirms `POST /api/maintenance/v1/search` and `tool_search_records()` return identical hits, order, RRF scores, and compatibility tiers.
2. **Trace Truthfulness & All 12 Stages (`test_trace_truthful_timings_counts_and_degradation`):**
   - Verified that all 12 stages are measured and reported in `trace.stages` and `trace.stage_timings_ms`:
     `queue`, `normalization`, `embedding`, `compatibility_filtering`, `raw_bm25`, `normalized_bm25`, `dense_cosine`, `fusion`, `dedup`, `rerank`, `top_k_selection`, `record_fetch`.
   - Verified that `dedup.count_out` reflects the deduplicated candidate pool size prior to top-k truncation.
   - Verified that reranker degradation branch (`reranker_unavailable`) is truthfully recorded when quality mode is enabled without reranker.
3. **Pagination, Bounds, and Canonical Mentions Filter (`test_lab_records_pagination_bounds_and_filtering`, `test_canonical_mentions_component_filter`):**
   - Verified page size bounds, offsets, total and total_pages calculations.
   - Verified that canonical mentions mapping handles relations (e.g. `CYL` token matching canonical component `cylinder`).
   - Verified 404 response on invalid corpus UUID.
4. **Deterministic 2D PCA Projection (`test_lab_projection_deterministic_provenance_and_max_points`, `test_projection_cache_isolation_across_engines`):**
   - Verified coordinates are identical across repeated calls.
   - SVD sign convention forces dominant principal components positive for determinism.
   - Verified provenance metadata: method `deterministic_centered_pca2_svd`, explained variance, model ID, model revision, source hash.
   - Verified max points slicing on response without mutating cached full projection.
   - Verified independent cache isolation across distinct engine instances.
5. **Facility Domain Invariants (`test_facility_null_actions_and_real_source_fields`):**
   - Verified facility records return `action_raw: null` and `action_normalized: null` while preserving all original fields and SHA256 hashes.
6. **Authentication & Origin Protection (`test_auth_and_origin_refusal`):**
   - Verified 401 `identity_expired` when cookie is tampered or missing.
   - Verified 403 `origin_not_allowed` on mutating requests from unauthorized origins.
7. **Storage & Quota Metrics (`test_lab_storage_quota_and_source_labels`, `test_storage_null_database_bytes_and_error_handling`):**
   - Verified quota 500,000,000 bytes labelled `Free plan database quota (configured 500MB)`.
   - Verified truthful `database_status: "unavailable"` / `"error"` with `database_bytes: null` when database is disconnected or failing, with separate dense vector float32 memory and record counts.

---

## 4. Local Server Startup

To run the local server on port 8102 (from `/Volumes/MAC/Projects_devolopment/nexai_gdd_retrieval_lab`):
```bash
uv run python -m uvicorn api.main:app --host 127.0.0.1 --port 8102
```
Workbench URL: `http://localhost:8102/retrieval-lab`

---

## 5. Limitations

1. **Reranker Availability:** The cross-encoder reranker is intentionally disabled by default (`rerank_enabled: false`), as specified. When quality mode is toggled in the UI, the engine truthfully records the degraded branch `reranker_unavailable` in the response trace.
2. **2D PCA Projection Scope:** The projection is an exploratory inspection tool based on linear centered PCA over the normalized 384-dimensional dense vectors. As explicitly noted in the UI and API metadata (`inspection_only_not_retrieval_score`), 2D Euclidean distance on the plot is for visualization and does not represent hybrid retrieval relevance scores (which combine BM25 raw, BM25 normalized, dense cosine, compatibility tier, and RRF fusion).
3. **Database vs In-Memory Storage:** In testing/offline environments where PostgreSQL is not attached, database table sizes and database bytes are reported as `null` with `database_status: "unavailable"`. In-memory dense matrix float32 buffer memory is reported independently.

---

## 6. Git Status & Commit Reference

- **Base Commit:** `1e131c2`
- **Branch:** `gdd/retrieval-lab`
- **Working Tree:** Reviewed worker checkpoint integrated into the canonical development checkout.
- **Commit SHA:** `ee40b9989ed784180376d6edf688f76d4de40c9a` (reviewed worker checkpoint)
