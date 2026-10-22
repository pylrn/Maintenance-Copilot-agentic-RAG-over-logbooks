# Maintenance Atlas

Predictive Intelligence for Logbook Operations & Troubleshooting.

Project repository: [pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks](https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks). All project development commits should target this repository; person one uses `person-1-retrieval-platform`.

Person one's retrieval/platform implementation for NEXAI PS 1.3. The development root is `/Volumes/MAC/Projects_devolopment/nexai_implimentation`; the planning source remains `/Users/kush/Documents/ChatGPT/maintainence copilot`.

Implemented: source-preserving aviation/facility ingestion, PostgreSQL 17/pgvector storage, immutable corpus/evidence schema, true raw/normalized BM25 plus exact BGE cosine search, RRF/compatibility/duplicate grouping, deterministic comparison/pattern/sensitivity services, signed anonymous identity/Origin checks, source-version lookup, shared typed contracts/marked fixtures, startup readiness and API composition.

Person two's agent, evidence-release gate, durable workflow implementation and Talent frontend are **not yet integrated**. `/maintenance` deliberately returns `person_two_ui_pending` until their UI exists. Read [the integration handoff](docs/p1/PERSON_2_HANDOFF.md) before implementing that side. Shared schemas are a P1 baseline awaiting P2 review, not a claimed joint signoff.

## Local setup

Python 3.11, `uv`, Docker and access to the public model download are needed. Run from this repository. A local `.env` and isolated PostgreSQL volume have already been created on this machine; do not overwrite them. On a new machine, copy `.env.example` to `.env`, supply a random DB password and 32+ byte signing secret, and align the password in `DATABASE_URL`. API keys remain server-only. No live DeepSeek key has been configured by this work.

```sh
uv sync --frozen --extra dev
docker compose up -d db
uv run python -m scripts.ingest --migrate
```

`.env` is ignored. PostgreSQL listens on loopback port 55432; the API uses port 8000. For person two on the same machine, use a separate Compose project, DB volume/name and ports. Do not point development at another person's private sessions.

## Source data and models

Download or use the inspected original CSVs. Raw datasets, vectors, models and user uploads are intentionally ignored in Git. The retained research files on this machine are in `/Users/kush/Documents/NEXAI_Maintenance_Research_20261021/raw/`.

```sh
uv run python -m scripts.ingest --domain aviation --source /path/to/maintnet_aviation_dataset_deidentified.csv --expected-sha256 a70daa27ba9c44a68617d69be1352be7fde003145ca142cbe0b7b51e197c6c3a
uv run python -m scripts.ingest --domain facility --source /path/to/Facility_Maintenance200.csv --expected-sha256 cd3d17441f1066fed3a232646480a05848318f71f72c57a5e28dc2f96b345736
uv run python -m scripts.build_indexes --download
```

The fixed BGE revision is `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`; it is in `.env.example` and the local `.env`. Index build precomputes both problem-only and problem+action vectors, persists them in pgvector, and atomically writes checksum-verified NPZ/manifest artifacts. Each corpus/model/representation retains source order and document hashes. Startup loads cached models only and rejects mismatches; it never downloads on a judge's first query. Set `EMBEDDING_REVISION` to the artifact revision if intentionally rebuilding with a different model commit. A representation change requires a new artifact build.

The aviation snapshot has 6,169 original rows and 5,122 distinct raw problem/action pairs. Facility has 200 rows and 190 distinct descriptions; no corrective-action field. `RecordSnapshot.source_file_sha256` identifies the CSV, while `field_sha256` and citation `source_sha256` identify decoded raw field text encoded in UTF-8. Offsets are Python Unicode code points, not JavaScript UTF-16 indices. Truncation flags are explicitly heuristic and never restore missing text. No visual mapping is claimed before P2's catalog review.

Original releases: [aviation](https://people.rit.edu/fa3019/technical/aircraft.html), [facility](https://people.rit.edu/fa3019/technical/facility.html). Retain MaintNet attribution and check redistribution terms; a paper's license does not automatically license every dataset derivative. Historical logs are not approved model-specific maintenance procedures. No aircraft identity/model/chronology or repair-success rate can be inferred from these fields.

## Run and exercise the API

```sh
uv run python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Use `http://localhost:8000`, matching `APP_ORIGIN`. A browser origin of `http://127.0.0.1:8000` is different; configure it explicitly if that is the desired browser URL. No wildcard credentialed CORS is enabled.

```sh
curl http://localhost:8000/api/maintenance/v1/health
curl http://localhost:8000/api/maintenance/v1/capabilities
curl -c /tmp/maintenance-cookie -H 'Origin: http://localhost:8000' -H 'Content-Type: application/json' -d '{"query_raw":"#2 intake leaking","domain":"aviation","top_k":5}' http://localhost:8000/api/maintenance/v1/search
```

Read an exact record with `GET /api/maintenance/v1/records/aviation/100009?corpus_id=2795c1d6-a5f4-5c8d-a773-4ac724d10e99`. Explicit corpus versions also support historical lookup after the active index changes. Search is not an answer endpoint: hits, component compatibility, scores and differences do not certify a fix. Public source corpora are readable; private session authorization is P2's workflow boundary using `require_session_owner`.

`GET /health` reports platform readiness and P2 readiness separately. `configured_models` in capabilities is a server allowlist, not a provider-account smoke result. A missing/failed index reports a typed 503 rather than claiming no fault exists. Required production settings reject placeholder credentials, unpinned embeddings and non-HTTPS origin.

## Contracts and parallel work

Canonical types: `maintenance/contracts.py`. Generated schema/fixtures: `contracts/v1/`; regenerate with `uv run python -m contracts.v1.export`. Fixtures are synthetic and marked `fixture_only`; never use them as real evidence or measured runs. The full owner table and behavior specification remain in `docs/work-split/`. P1 owns all shared migrations/config/dependencies/app composition. P2 writes `api/routes/workflows.py` and their assigned agent/UI/workflow modules. The app discovers that aggregator on restart. Do not edit another owner's files to resolve an interface mismatch; request a contract/migration revision.

## Checks and evaluation

```sh
uv run ruff check maintenance api scripts tests contracts/v1
uv run python -m pytest -q
uv run python -m scripts.evaluate
```

Without `TEST_DATABASE_URL`, real PostgreSQL tests skip explicitly. To run them, create a **separate test database**, migrate it with `Database.migrate()`, then supply its DSN via `TEST_DATABASE_URL`. Never use a live user database. See `docs/p1/verification.md` for the checks actually run on this machine.

[Retrieval results](docs/p1/retrieval-evaluation.md) use 15 pre-run frozen provisional engineering queries and exact-PROBLEM-group labels. Human label review remains pending, and broader valid evidence may be unlabeled. The full JSON records per-query hits, source/model versions and timings. Agent citation precision, refusal quality, LLM costs and public-hosting latency are unmeasured pending P2. Do not tune on these questions and continue calling them held-out.

## Container and deployment

`Dockerfile` builds a non-root API image; Compose's `app` profile mounts prebuilt models/artifacts and connects to its DB service. CPU PyTorch on Linux avoids unused CUDA dependencies; source follows [uv's official PyTorch guide](https://docs.astral.sh/uv/guides/integration/pytorch/). `uv.lock` is the cross-platform resolver lock, and `requirements.lock` is its hashed export. Local native and container runtimes are checked separately; no live provider round trip is implied by resolving PydanticAI dependencies.

```sh
docker compose --profile app up -d --build
```

This is local infrastructure, not a public deployment. Before public release: integrate P2, configure DeepSeek API access, choose a host with enough RAM/storage and persistent PostgreSQL, use TLS/HTTPS and its exact origin, configure server secrets, package the pinned artifacts, verify SSE buffering/replay/restart and owner isolation, then run positive/refusal/citation browser checks on the real public URL. Production uploads need a persistent owner-scoped storage service chosen with P2. See `docs/p1/deployment-runbook.md`.

No credentials, raw source datasets, private conversations or embeddings were committed. No public deployment or submission was created. Person-one changes are published on their development branch for review; existing main-branch history and files are preserved. Source/reuse provenance is in `reference/hybrid-search/SOURCE_MANIFEST.json`; copied reference code stays unchanged.
