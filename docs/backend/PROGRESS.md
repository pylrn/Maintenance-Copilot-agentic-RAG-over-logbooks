# Maintenance Copilot Backend Progress

## Status Overview
- **Branch:** `gdd/local-retrieval-providers`
- **Working Directory:** `/Volumes/MAC/Projects_devolopment/nexai_gdd_backend`
- **Isolated Ports:** API on `8100` (preserving existing API on `8000`)
- **Isolated Databases:** `maintenance_gdd_integration`, `maintenance_gdd_tests` on `localhost:55432`
- **Managed Supabase Status:** Remote project `cjtokhnlwoqjeifmnwho` (PostgreSQL 17.11) verified with private `maintenance` schema and `extensions.vector`. Verified root certificate at `data/certs/supabase-root-2021.crt`. DSN profile in `.env.supabase`. Safe preflight via `scripts/db_preflight.py` passing with 0 unredacted secrets. Optional docker override in `compose.supabase.yaml`.
- **Provider Status:** DeepSeek baseline and Google Gemini provider implemented via OpenAI-compatible endpoint (`https://generativelanguage.googleapis.com/v1beta/openai/`) supporting allowlisted models `gemini-3.8-flash` and `gemini-2.5-flash`. Safe smoke test in `scripts/provider_smoke.py` with redacted error output.
- **Current Status:** 100% complete across all stages. All 65 tests passing. Live API on port 8100 verified for Aviation and Facility retrieval, raw record fetching, session lifecycle, and exact claim evidence storage.

---

## Stage Checklist

### Stage 1: Baseline Snapshot & Repository Hygiene
- [x] Create `docs/backend/PROGRESS.md`
- [x] Snapshot commit (`79915c7`) of intentionally copied pending source files (no secrets)
- [x] Verify read-only symlinks (`.venv`, `models`, `artifacts`) and isolated environment
- [x] Confirm raw CSV checksums for Aviation (`2795c1d6-a5f4-5c8d-a773-4ac724d10e99`) and Facility (`b5f9d886-1b2c-56cc-96fe-ae0488597043`)

### Stage 2: Database Lifecycle, Managed PostgreSQL / Supabase & Isolation
- [x] Verified migrations 001-006 exist and match digests
- [x] Added explicit schema and search_path support in `maintenance/db.py` (`maintenance,extensions,pg_catalog` vs default `public`) with strict regex identifier validation
- [x] Added vector schema dynamic registration in `maintenance/db.py` (supporting `extensions` and `public`)
- [x] Added TLS / SSL context support with custom root certificate (`DATABASE_SSL_ROOT_CERT`) and `statement_cache_size=0` for transaction poolers
- [x] Created `scripts/db_preflight.py` safe preflight command to verify DSN profiles without mutating remote state or leaking secrets
- [x] Created optional `compose.supabase.yaml` Docker Compose override with read-only cert bind mount `/app/certs/supabase-root-2021.crt`
- [x] Ingested and seeded isolated database `maintenance_gdd_integration` with Aviation (6169 rows) and Facility (200 rows) corpora, plus 12,738 precomputed vectors in `record_embeddings`

### Stage 3: Gemini Provider & Tool Roundtrip Support
- [x] Added Gemini settings (`gemini_api_key`, `gemini_base_url`, `gemini_model`) and allowlist (`deepseek-flash`, `gemini-3.8-flash`, `gemini-2.5-flash`) in `maintenance/config.py`
- [x] Implemented Gemini provider adapter alongside DeepSeek in `maintenance/models/provider.py`
- [x] Ensured non-thinking mode for DeepSeek, standard OpenAI format for Gemini, `SecretStr` for keys and credentials redaction in `__repr__`
- [x] Fixed `tool_search_records` and `tool_get_records` in `maintenance/tools.py` for `SearchHit` attributes (`rrf_score`) and exact ID retention
- [x] Implemented bounded `roundtrip_tool_loop` in `maintenance/models/provider.py` with wall-clock timeout and tool budget exhaustion handling
- [x] Kept retrieval independent of LLM keys (deterministic extractive fallback renders supported historical claims with exact quotes and field checks)
- [x] Added mocked provider tests in `tests/agent/test_providers.py` and safe smoke command in `scripts/provider_smoke.py` with redacted error output

### Stage 4: Retrieval Engine Implementation & Refinement
- [x] Raw + normalized BM25 (filtered at score > 0) + pinned BGE dense recall (50/channel)
- [x] Weighted RRF fusion (weights: 0.5 raw BM25, 0.5 normalized BM25, 1.0 dense; k=60)
- [x] Explicit compatibility checking: component, symptom, number, laterality, negation
- [x] Duplicate grouping preserving member record IDs and raw counts
- [x] Safe raw-record batch fetching and 6-representative evidence selection
- [x] Optional bounded cross-encoder reranker (max 20 pairs off-thread with `asyncio.shield` concurrency protection and timeout degradation)
- [x] Query normalization and constraint-preserving rewrites

### Stage 5: Acceptance & Verification
- [x] Pytest full test suite passing with `PYTHONPATH=.` (69 passed in 1.81s)
- [x] Facility `DESCRIPTION` field and hash preservation, zero fabricated `ACTION` evidence IDs, and deterministic validation gate applied to all released answers (including extractive fallback)
- [x] Malformed DSN redaction requiring valid postgresql scheme and non-empty hostname before parsing
- [x] Ruff lint checks clean across `api maintenance scripts tests` (0 errors)
- [x] Live HTTP verification on port 8100:
  - `/api/maintenance/v1/health` returning `ready: true`, all subsystems ready
  - `/api/maintenance/v1/search` for Aviation returning 6 hits across raw BM25, normalized BM25, and dense channels
  - `/api/maintenance/v1/search` for Facility returning 6 hits with `action_raw: null` and zero invented actions
  - `/api/maintenance/v1/records/aviation/{source_id}` and `facility/{source_id}` fetching exact records with field SHA256 hashes
  - Full session lifecycle creating run, executing runner, saving 12 exact evidence snapshots with text SHA256 hashes, and committing answer
  - Cross-owner 404 access control verified for `/runs/{run_id}/events`
- [x] Domain checks (facility ACTION prevention, corpus ID match, field type validation)
- [x] Verified Docker Compose override with `docker compose --env-file .env --env-file .env.supabase -f compose.yaml -f compose.supabase.yaml config --quiet`
- [x] Generated `docs/backend/REPORT.md` and `docs/backend/READY_FOR_REVIEW.json`
- [x] Final local snapshot commit on `gdd/local-retrieval-providers`
