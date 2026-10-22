# Schema and persistence requests from Person 2 (Agent, UI & Workflows) to Person 1 (Platform & Retrieval)

## Date: 2026-10-22
## Target Contract: maintenance/v1

### 1. Database Migrations Needed (from IMPLEMENTATION_PLAN.md Section 4 & 5)
Person 2 relies on the PostgreSQL 17 + pgvector schema. Please ensure the following tables and constraints are included in `db/migrations/`:

- `corpus_versions` (domain enum: 'aviation', 'facility', sha256, record_count, etc.)
- `maintenance_records` (corpus_id, record_id, csv_row, original_fields jsonb, problem_raw, action_raw, problem_normalized, action_normalized, duplicate_key, etc.)
- `record_embeddings` (vector(384) for 'problem' and optional 'problem_action')
- `sessions` (session_id UUID PK, owner_id UUID, domain, state_revision integer DEFAULT 0, aircraft_profile jsonb, board jsonb DEFAULT '{"known":[],"reported":[],"missing":[]}', status, timestamps)
- `runs` (run_id UUID PK, session_id FK, parent_answer_id FK, mode CHECK ('EVIDENCE','HYPOTHESIS','CHALLENGE','SENSITIVITY','DISTINGUISH','HANDOVER'), idempotency_key UUID, request_hash char(64), state_revision int, corpus_ids jsonb, prompt_version, model_id, status CHECK ('queued','running','validating','completed','cancelled','failed'), lease_owner, lease_expires_at, timestamps, UNIQUE(session_id, idempotency_key))
- `run_events` (run_id FK, sequence bigint, event_type, public_payload jsonb, created_at, PRIMARY KEY(run_id, sequence))
- `messages` (message_id UUID PK, session_id FK, run_id FK, sequence bigint, role, source_type, content jsonb, created_at, UNIQUE(session_id, sequence))
- `search_runs` (search_id UUID PK, run_id FK, query_raw, search_spec jsonb, pipeline_version, channel_results jsonb, final_results jsonb, timings jsonb, limitations jsonb)
- `answers` (answer_id UUID PK, run_id FK UNIQUE, source_mode, envelope jsonb, validation_report jsonb, released_at)
- `evidence_snapshots` (evidence_id UUID PK, run_id FK, corpus_id + record_id FK, field enum, raw_text, text_sha256, fetched_at)
- `claim_supports` (answer_id FK, claim_id, kind enum ('log_span', 'aggregate_receipt', 'search_comparison'), nullable evidence_id FK, nullable receipt_id FK, quote, start, end, source_sha256)
- `model_messages` (run_id FK, turn_index, serialized PydanticAI messages, adapter_version, provider)
- `hypothesis_requests` (request_id UUID PK, owner_id, session_id FK, parent_answer_id FK, parent_hash, state_revision, requested_at, mode_label)
- `computed_receipts` (receipt_id UUID PK, run_id FK, kind enum ('aggregate', 'search_comparison'), corpus/search versions, parameters, result JSON, manifest hash, validator version)
- `pinned_evidence` (session_id, corpus_id, record_id, pinned_at, user_note)
- `feedback` (answer_id, owner_id, reason enum, source_ids, user_note, review_status)

### 2. Service Interface Requirements
P2 routes will consume P1's service interfaces via dependency injection on `FastAPI.app.state`:
- `search_service.search(spec: SearchSpec, scope: RunScope) -> SearchResult`
- `record_service.fetch(record_ids: list[str], scope: RunScope) -> list[RecordSnapshot]`
- `pattern_service.summarize(filters: dict, scope: RunScope) -> PatternSummary`
- `comparison_service.compare(record_ids: list[str], scope: RunScope) -> ComparisonReceipt`
- `sensitivity_service.compare_specs(base_spec: SearchSpec, variants: list[SearchSpec], scope: RunScope) -> SensitivityReceipt`

### 3. Application Mounting Agreement
- P1 owns `api/main.py`.
- P1 mounts P2's router aggregator: `app.include_router(workflows_router, prefix="/api/maintenance/v1")`.
- P2 owns `api/routes/workflows.py` which aggregates subrouters (`sessions`, `runs`, `actions`, `visuals`, `uploads`, etc.).
