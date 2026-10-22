# Verification record — 22 October 2026

Native platform checks were performed on the requested development volume using Python 3.11.12 and the resolved uv environment. They do not establish agent/UI readiness.

- `ruff check maintenance api scripts tests contracts/v1`: passed.
- `python -m compileall -q maintenance api scripts`: passed.
- Full pytest with `TEST_DATABASE_URL` pointed at the separate `maintenance_test` database: **33 passed**, no skips. Covers lossless CSV/BOM/quoted multiline/duplicate source handling, checksums, explicit facility dates/null actions, normalization, RRF and lexical zero hits, dense/compatibility/duplicate behavior, corpus scope, deterministic counts/sensitivity, artifact checksum/model mismatch, strict contracts, signed/tampered/expired identities, Origin checks, service-error separation, synthetic fixture validation, PostgreSQL source immutability/idempotent imports, archived source lookup, owner lookup, one-live-run and nonnegative revision constraints.
- All six migration checksums applied; schema readiness returned true. PostgreSQL contains **6,369 source records** and **12,738 stored vectors** across two representations (problem and problem+action).
- Original aviation checksum/count: 6,169 rows / 5,122 distinct problem/action pairs. Facility checksum/count: 200 rows / 190 distinct descriptions.
- All 44 immutable copied hybrid-search files verified against their SHA-256 manifest.
- Live native HTTP checks: health 200 with database/retrieval ready and workflows false; aviation search returns actual raw BM25, normalized BM25 and dense paths; source-version lookup returns original problem/action; facility search returns real hits. Incorrect Origin is rejected. No browser chat/UI result is claimed.
- Frozen provisional retrieval checks: raw BM25 Hit@5 11/15, dense-only 12/15, hybrid RRF 12/15, compatibility/grouping hybrid 12/15. Exact versioned measurements are in `retrieval-evaluation.json`; human label review remains pending. No held-out threshold tuning occurred.

## Reproduce database tests

Create a separate PostgreSQL test database and migrate it. The local `maintenance_test` has already been created and migrated. Keep credentials in the environment, never paste them into this file.

```sh
uv run python - <<'PY'
import asyncio, os, pytest
from maintenance.config import Settings
from maintenance.db import Database
url = Settings().database_url.get_secret_value().rsplit('/', 1)[0] + '/maintenance_test'
async def prepare():
    db = Database(url)
    await db.open()
    await db.migrate()
    await db.close()
asyncio.run(prepare())
os.environ['TEST_DATABASE_URL'] = url
raise SystemExit(pytest.main(['-q']))
PY
```

Test source rows and sessions are isolated from the application database. A missing TEST_DATABASE_URL explicitly skips the database suite; it is not a passed integration check.

## Still requires integration

Live DeepSeek authentication/tool/structured-output round trip; P2's evidence gate and mode isolation; durable workflow replay/restart/cancellation; human citation/refusal scoring; browser chat and 2D visual behavior; selected host and HTTPS public URL. Optional reranker has not been enabled or benchmarked. P2 contract/schema review is pending. Container build/runtime evidence is appended separately after it finishes.

The resolved PydanticAI Agent/OpenAIChatModel/OpenAIProvider imports succeeded without a key or outbound provider request. This verifies installation only, not provider behavior. Running the ordinary no-DSN pytest command yielded 29 passed / 4 explicitly skipped database tests; the separate full run above included all 33 tests.

## Container verification

- `docker build -t maintenance-atlas:p1 .`: passed with the current source and hashed dependency export; repeat build reused the dependency layer.
- `docker compose --profile app up -d --no-build api`: passed. The API is now running in Docker on `http://localhost:8000`; PostgreSQL remains persistent in the project-specific volume.
- Live container HTTP: platform health 200, real three-channel aviation search 200, exact source-version lookup 200, facility search 200. `workflows_ready=false`, provider unconfigured and `/maintenance` 503 correctly reflect the missing P2 integration.
- Container process UID is 10001; `torch==2.14.1+cpu`, CUDA unavailable as intended. `uv pip check --system` checked 84 installed packages and reported compatibility.
- Details are recorded in `container-smoke.json`; deterministic real-corpus computation checks are in `computation-smoke.json`.
