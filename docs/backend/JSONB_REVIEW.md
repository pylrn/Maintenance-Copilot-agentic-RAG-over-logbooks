# Workflow JSONB Encoding Review & Root Cause Analysis

## Summary
Fixed double-encoding of JSONB fields in `maintenance/session_repository.py`. PostgreSQL `jsonb_typeof()` on stored rows now returns native types (`object`, `array`) instead of `string`. Legacy double-encoded string decode compatibility in `get_session()` is preserved without schema changes or data migrations.

## Root Cause
In `maintenance/db.py`, the asyncpg connection pool initialization registers custom codecs for PostgreSQL `json` and `jsonb` data types:
```python
for typ in ["json", "jsonb"]:
    await conn.set_type_codec(
        typ, encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
```
Whenever a parameter bound to a JSONB column is supplied to asyncpg, asyncpg automatically invokes `encoder=json.dumps` on it.
However, `SessionRepository` previously performed manual serialization prior to passing parameters to queries:
- Calling `json.dumps(...)` on dicts/lists
- Calling `answer.model_dump_json()` on Pydantic models

When asyncpg received these already-serialized JSON strings, it ran `json.dumps()` a second time. PostgreSQL received a JSON string literal (e.g. `'"{\"headline\": ...}"'`), resulting in `jsonb_typeof(...) == 'string'` instead of `'object'` or `'array'`.

## Changed Files & Remediation

### 1. `maintenance/session_repository.py`
All writes to JSONB columns now pass native Python objects (`dict`, `list`, or `model_dump(mode="json")`), leaving JSON serialization to the database connection codec:
- **`create_session`**:
  - `aircraft_profile`: passes `aircraft_profile or {}` (Python `dict`)
  - `board`: passes `{"known": [], "reported": [], "missing": []}` (Python `dict`)
- **`update_session_profile`**:
  - `aircraft_profile`: passes `aircraft_profile` (Python `dict`)
- **`create_run`**:
  - `corpus_ids`: passes `[str(cid) for cid in corpus_ids]` (Python `list`)
  - user message `content`: passes `{"text": request_text}` (Python `dict`)
- **`commit_answer_and_state`**:
  - `answers.envelope`: passes `answer.model_dump(mode="json")` (Python `dict`)
  - `answers.validation_report`: passes `validation_report` (Python `dict`)
  - `claim_supports.result_keys`: passes `sup.result_keys` (Python `list`)
  - `sessions.board`: passes `[b.model_dump(mode="json") for b in new_board_items]` (Python `list`)
  - assistant message `content`: passes `answer.model_dump(mode="json")` (Python `dict`)
- **`save_model_messages`**:
  - Already passed native Python `list[dict[str, Any]]`; kept correct.
- **`get_session`**:
  - Preserved legacy string fallback decode logic (`isinstance(..., str)` checks) to transparently read historical rows without migration.

### 2. `tests/workflows/test_jsonb_storage.py` (New)
Added regression test suite covering:
- Native `jsonb_typeof` assertion on stored rows for `sessions` (`aircraft_profile`, `board`), `runs` (`corpus_ids`), `messages` (`content`), `answers` (`envelope`, `validation_report`), and `claim_supports` (`result_keys`).
- Full roundtrip with `get_session()` and `save_model_messages()`.
- Backward-compatibility verification for legacy double-encoded string rows.

### 3. `docs/backend/JSONB_REVIEW.md` (New)
This review report.

## Check Commands

```bash
cd /Volumes/MAC/Projects_devolopment/nexai_gdd_jsonb
PYTHONPATH=. .venv/bin/pytest -q tests/workflows/test_jsonb_storage.py
.venv/bin/ruff check maintenance/session_repository.py tests/workflows/test_jsonb_storage.py
```

## Results
- `pytest tests/workflows/test_jsonb_storage.py`: 3 passed in 0.86s
- `ruff check`: All checks passed with 0 errors
- Full test suite (`pytest -q`): 73 passed in 2.25s
