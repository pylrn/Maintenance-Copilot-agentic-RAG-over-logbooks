# Maintenance Copilot Local Retrieval Backend & Provider Verification Report

## 1. Executive Summary
This report documents the implementation, hardening, and verification of the Maintenance Copilot retrieval backend on branch `gdd/local-retrieval-providers` at `/Volumes/MAC/Projects_devolopment/nexai_gdd_backend`.

Key deliverables achieved:
1. **Managed PostgreSQL / Supabase Compatibility:** Full support for configurable schemas (`maintenance`), extension schemas (`extensions.vector`), TLS CA verification (`data/certs/supabase-root-2021.crt`), and session pooler / PgBouncer compatibility (`statement_cache_size=0`). Validated against remote Supabase project `cjtokhnlwoqjeifmnwho` (PostgreSQL 17.11) via safe preflight and docker override.
2. **Multi-Provider LLM Integration:** Google Gemini provider added alongside DeepSeek via official OpenAI-compatible endpoint (`https://generativelanguage.googleapis.com/v1beta/openai/`) with strict model allowlist (`deepseek-flash`, `gemini-3.8-flash`, `gemini-2.5-flash`), `SecretStr` redaction, and bounded tool-call loop retaining tool call IDs.
3. **Retrieval Engine & Fallback Independence:** Deterministic extractive fallback operating independently of LLM API keys. 3-channel retrieval (raw BM25, normalized BM25, pinned BGE dense recall at 50/channel) with weighted RRF fusion (0.5, 0.5, 1.0; k=60), explicit compatibility tiering, duplicate collapsing, and evidence extraction.
4. **End-to-End Verification:** 100% test pass rate across 65 tests in `pytest`. Live HTTP verification on isolated port 8100 covering Aviation search, Facility search (no invented actions), raw record fetch, session lifecycle, evidence persistence, and cross-owner SSE authorization.

---

## 2. Architecture & Implementation Details

### 2.1 Database & Supabase Compatibility (`maintenance/db.py`)
- **Schema Separation:** Implemented custom connection initializers setting search path `f"{schema},{vector_schema},pg_catalog"` and dynamically registering pgvector in `vector_schema` (supporting `extensions` or `public`).
- **Identifier Sanitization:** Strict regex enforcement `^[a-zA-Z_][a-zA-Z0-9_]*$` on schema and vector schema parameters prevents SQL injection.
- **TLS CA Verification:** Supported custom CA root certificates (`DATABASE_SSL_ROOT_CERT`) with `ssl.CERT_REQUIRED` and server hostname verification.
- **Pooler Prepared Statement Safety:** Configurable `statement_cache_size` (set to `0` for transaction poolers / PgBouncer mode) prevents asyncpg prepared statement collisions.
- **Preflight Tool (`scripts/db_preflight.py`):** Read-only preflight script verifying table existence, vector extension, TLS handshake, and row counts with zero unredacted secrets printed.

### 2.2 LLM Providers & Native Tool Roundtrip (`maintenance/models/provider.py`)
- **Provider Adapters:** Single clean interface supporting DeepSeek (`https://api.deepseek.com`) and Gemini (`https://generativelanguage.googleapis.com/v1beta/openai/`).
- **DeepSeek Specifics:** Passes `extra_body={"thinking": {"type": "disabled"}}` to ensure deterministic execution.
- **Gemini Specifics:** Uses standard OpenAI chat completion formatting without unsupported thinking arguments; uses official models `gemini-3.8-flash` (default) and `gemini-2.5-flash`.
- **Security & Redaction:** Credentials wrapped in Pydantic `SecretStr`; `__repr__` displays `<LLMProvider type=gemini model=gemini-3.8-flash key=configured>` without leaking credentials. Exception handling in `scripts/provider_smoke.py` redacts arbitrary error bodies, outputting only exception class and HTTP status code.
- **Bounded Tool Loop (`roundtrip_tool_loop`):**
  - Enforces `max_retries=0` and hard wall-clock timeout.
  - Budgets `max_tool_calls` across turns, stopping further model invocations if budget is exhausted.
  - Retains exact `tool_call_id` and function names for all tool responses.
  - Handles timeout exceptions without hanging or dropping context.

### 2.3 Retrieval Engine & Evidence Integrity (`maintenance/retrieval/engine.py`, `maintenance/answer_validation.py`)
- **Recall Channels:**
  - Raw BM25 (top 50, filtered at score > 0)
  - Normalized BM25 (top 50, filtered at score > 0)
  - Dense semantic recall using pinned BGE-small-en-v1.5 embeddings (top 50)
- **Reciprocal Rank Fusion (RRF):** Weighted RRF formula with weights `0.5` raw BM25, `0.5` normalized BM25, `1.0` dense, and smoothing constant `k=60`.
- **Cross-Encoder Concurrency Shielding:** Reranker concurrency protected with `asyncio.shield` so timeouts return fast degraded unreranked hits without prematurely clearing `_reranker_busy` before the worker thread completes.
- **Evidence Verification:**
  - Rejects quotes attached to unsupported claim suffixes or negation inversions.
  - Verifies exact `corpus_id` match between claim and evidence.
  - Enforces field compatibility (e.g., `historical_action` cannot cite a `PROBLEM` field).
  - Persists exact text SHA256 hashes in `evidence_snapshots` table.

### 2.4 API Authorization & State Management (`api/routes/`)
- **Session & Run Ownership:** `GET /runs/{run_id}/events` verifies `s.owner_id == request_owner_id` via database lookup before subscribing to event stream, returning 404 for non-owners or invalid run IDs.
- **Model ID Provenance:** Active provider model (`gemini-3.8-flash`, `deepseek-flash`, or `extractive/v1`) is recorded in database `runs.model_id`.

---

## 3. Docker Compose & Deployment Seams

### 3.1 Compose Override (`compose.supabase.yaml`)
To prevent the base `compose.yaml` from overriding `DATABASE_URL` with the local docker container DSN, `compose.supabase.yaml` provides:
- Direct environment mapping from private configured environment: `${DATABASE_URL}`
- `DATABASE_SCHEMA: ${DATABASE_SCHEMA:-maintenance}`
- `VECTOR_SCHEMA: ${VECTOR_SCHEMA:-extensions}`
- Fixed container cert path: `DATABASE_SSL_ROOT_CERT: /app/certs/supabase-root-2021.crt`
- Read-only bind mount: `./data/certs:/app/certs:ro`
- `depends_on: !reset []` so the local docker db container is not started.

### 3.2 Validated Invocation Commands
```bash
# Validate configuration quietly without leaking secrets
docker compose --env-file .env --env-file .env.supabase -f compose.yaml -f compose.supabase.yaml config --quiet

# Launch API targeting managed Supabase
docker compose --env-file .env --env-file .env.supabase -f compose.yaml -f compose.supabase.yaml up -d api
```

---

## 4. Verification Evidence & Measured Metrics

### 4.1 Pytest Suite Execution
Command: `PYTHONPATH=. .venv/bin/pytest -v`
Result: **65 passed in 1.63s**

Breakdown:
- `tests/agent/test_agent.py`: 3 passed (extractive answer rendering, visual service context, unsupported torque request)
- `tests/agent/test_providers.py`: 18 passed (allowlist, TLS/CA rejection, credential redaction, DeepSeek non-thinking, Gemini format, bounded tool loop, claim validations, concurrency/timeout shield, JSONB array persistence)
- `tests/contracts/test_contracts.py`: 7 passed (mode restrictions, search filters, event privacy, identity signer)
- `tests/data/test_ingest.py`: 10 passed (BOM handling, format validation, checksum validation, facility literal NaN, no invented actions)
- `tests/integration/test_api.py`: 6 passed (origin checks, error handling, health redaction, capabilities reporting)
- `tests/integration/test_database.py`: 4 passed (migrations, immutable records, single live run, negative revisions)
- `tests/retrieval/test_artifacts.py`: 4 passed (bundle integrity, vector conflict rejection, revision acceptance)
- `tests/retrieval/test_engine.py`: 7 passed (deterministic RRF, zero-score lexical suppression, duplicate grouping, sensitivity receipt)
- `tests/ui/test_ui.py`: 1 passed (assets served)
- `tests/workflows/test_validation.py`: 3 passed (log span validation, quote mismatch, causal upgrade rejection)
- `tests/workflows/test_workflows.py`: 2 passed (visual context routes, complete lifecycle with cross-owner 404 and model_id check)

### 4.2 Live HTTP Verification (Port 8100)
1. **Health Check:**
   `curl -s http://127.0.0.1:8100/api/maintenance/v1/health`
   Output: `{"ready":true,"app_ready":true,"retrieval_ready":true,"database_ready":true,"workflows_ready":true,"startup_errors":[]}`

2. **Aviation Search:**
   `POST /api/maintenance/v1/search` with `query_raw: "cylinder intake leak"`, `domain: "aviation"`
   - Total hits: 6
   - Top hit: `aviation:100734`, RRF score `0.0164`, Tier: `direct`, Channel ranks: `{'dense': 1}`
   - Channel coverage: `bm25_normalized: 50`, `bm25_raw: 50`, `dense: 50`
   - Latency: Embedding `14.4ms`, Total retrieval `492.8ms`

3. **Facility Search:**
   `POST /api/maintenance/v1/search` with `query_raw: "chiller pump leak"`, `domain: "facility"`
   - Total hits: 6
   - Top hit: `facility:114335`, RRF score `0.0328`, Tier: `related`
   - `action_raw`: `null` (zero invented actions; preserved original `DESCRIPTION`)
   - Latency: Embedding `49.5ms`, Total retrieval `65.8ms`

4. **Record Fetch:**
   `GET /api/maintenance/v1/records/aviation/100734`
   - Exact problem: `"CYL #1 INTAKE LEAKS."`
   - Exact action: `"REMOVED & REPLACED CYL #1 INTAKE GASKET."`
   - Verified field SHA256 hashes present for all fields.

5. **Live End-to-End Session Execution:**
   - Session created: revision 0
   - Evidence message posted: run ID created
   - Extractive runner executed in background: 12 evidence records fetched and 12 snapshots written to `evidence_snapshots` table with valid SHA256 hashes
   - Run transitioned to `status: completed`
   - Answer committed to `answers` table with validation report `{"valid": true, "claims_count": 12, "evidence_checked": 12}`
   - Handover generated: `GET /sessions/{id}/handover` returned complete markdown investigation summary.

6. **Database Integrity & Conflict Smoke:**
   - Identical hash, conflicting vector: rejected (`vector_conflict`).
   - New model revision: accepted.
   - Cross-owner access to `/runs/{id}/events`: rejected with `404 Not Found` (`run_not_found`).

### 4.3 LLM Provider Smoke & Verification Status
- **Model Discovery:** Verified via official OpenAI-compatible endpoint (`client.models.list()`), successfully discovering `gemini-3.8-flash` and `gemini-2.5-flash`. Model enumeration alone proves key authentication against the discovery endpoint, but does not prove valid generation authorization or upstream availability for specific model variants.
- **Generation Status (Gemini):**
  - `gemini-2.5-flash`: chat generation endpoint returned HTTP 404 on current endpoint.
  - `gemini-3.8-flash`: default 12s request timed out; minimal thinking returned 400 (explicitly unsupported); `reasoning_effort="low"` with 30s deadline timed out; independent native `generateContent` 20s POST also resulted in `ReadTimeout`.
  - **Verdict:** External Gemini generation availability is recorded as **unverified** due to upstream endpoint timeouts. The API key successfully authenticated against model enumeration.
  - **Fallback Independence:** The retrieval backend and extractive reasoning pipeline operate completely independently of external LLM availability. When providers are unconfigured or unavailable, the system safely and deterministically serves verified historical claims with exact quote spans and field constraints.
- **DeepSeek Status:** Configured with non-thinking flags. Note that while non-thinking flags disable reasoning mode, they do not provide a deterministic guarantee of identical tokens across model revisions. Determinism is strictly maintained by the verified local extractive retrieval engine.

### 4.4 Facility Field Preservation & Deterministic Release Gate
- **Facility Domain Preservation:** In Facility records (`parse_facility`), `field_sha256` contains `DESCRIPTION` only. `tool_get_records` registers `field="DESCRIPTION"` with the non-empty SHA256 of the description text, and avoids generating fabricated `ACTION` fields or evidence IDs.
- **Field-Specific Template Gate:** `validate_claim` strictly permits `DESCRIPTION` as historical description/problem (`Record {rid} records description: "{q}"` or `problem`), but rejects citations of `DESCRIPTION` on `historical_action` claims with `claim_type_field_mismatch`.
- **Deterministic Release Gate:** Applied `validate_answer` to all released answers—including extractive fallback. If any claim contains corrupted hashes or quote mismatches, the gate rejects the unverified claims and falls back to an `insufficient_evidence` response with full error provenance in `validation_report`.
- **Malformed DSN Redaction:** `scripts/db_preflight.py` requires a valid `postgresql`/`postgres` scheme and non-empty hostname before parsing, preventing key-value DSNs (e.g. `password=FAKE_SECRET`) from leaking in output fields.

---

## 5. Security & Isolation Commitments
- **Zero Remote Git Actions:** No commits pushed, no PRs opened, no comments made.
- **Zero Leaked Credentials:** All API keys and database passwords stored in private untracked `.env` files; error outputs redacted in smoke tests and preflight scripts.
- **Isolated Runtimes:** Isolated database `maintenance_gdd_integration` and test database `maintenance_gdd_tests` at port 55432; isolated API at port 8100.
- **Original Checkout Untouched:** All code changes and execution contained exclusively within `/Volumes/MAC/Projects_devolopment/nexai_gdd_backend`.
