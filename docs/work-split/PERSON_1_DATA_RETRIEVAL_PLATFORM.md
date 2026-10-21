# Person one: data, hybrid retrieval and platform

You own the original-data-to-versioned-evidence boundary and the shared infrastructure. Person two owns the agent, released answers, workflow persistence and product UI. This division keeps independent work possible while giving every shared file exactly one writer.

Your deliverable is not a search notebook: it is an injectable, tested maintenance retrieval service plus reproducible ingestion, schema/migrations, app composition, credentials/configuration, deployable build and measured retrieval report. Person two should be able to replace fixture services with your real services without rewriting their agent or frontend.

## Your execution order

### P1.1 — Bootstrap and freeze the joint contract (first shared checkpoint)

1. Read the source plan and immutable reference manifest. Inventory current workspace; preserve the existing plan/prompt/assets. Establish the agreed Git baseline, ignore secrets/private data, and create the shared package layout. Do not install the copied recruiting project as the new app.
2. Create the maintenance `pyproject.toml` with Python 3.11 and selected core dependencies. Ask P2 for their provider/extraction/test dependency list before resolution; P2 does not edit the manifest. After P2's provider smoke test, commit the exact tested lock.
3. Implement validated settings, app factory, DB pool and server-owned identity dependency. Prepare `.env.example`, Compose PostgreSQL 17 + pgvector and health/readiness checks. Each developer gets an isolated DB/schema and local environment.
4. Author `contracts/v1/`, `maintenance/contracts.py`, realistic but explicitly synthetic fixtures, and fake injectable retrieval interfaces. P2 reviews required workflow/answer/event fields. Keep incompatible changes out of parallel branches until agreement.
5. Apply all initial migrations for source, sessions, evidence, receipts and visuals from plan section 4. Include unique active-run, message/event sequencing, immutable source-version and ownership constraints. Incorporate P2's schema requests before they integrate persistence.

**Handoff:** P2 receives a committed contract version, pool/auth/settings interfaces, sample session/search/record/answer/event/error fixtures, importable fake services and migration commands. P2 supplies route aggregator plus lifecycle interface. P1's composition mounts it once.

### P1.2 — Reproducible source ingestion

1. Use the inspected raw CSV snapshots; parse aviation as UTF-8 with BOM handling, validate exact headers, IDs, row counts and expected checksum. Preserve original PROBLEM/ACTION and csv row provenance. Ingest is idempotent by domain+source hash; changed files produce a new corpus version.
2. Facility adapter preserves all six fields, DESCRIPTION as problem and action null. Expose original dates/site/type without manufacturing equipment identity or outcomes. Apply explicit parsing and uncertainty markers from the plan.
3. Normalization produces additional search text, never replacement citation text. Review shorthand maps and conflicts; preserve token boundaries, negation, units, part strings, numbers and laterality. Flag suspected truncation without completing it. Use P2's reviewed component IDs/catalog revision for span-backed annotations; unknown mappings stay unknown.
4. Build duplicate keys; retain every source row and distinct-pair counts. Generate an import manifest containing origin/rights notes, file hash, corpus ID, row counts, field schema, parser/normalizer/catalog versions and warnings.
5. Test wrong header/hash, duplicate ID, BOM, quoting/newlines, null facility action and repeat import. Preserve dataset attribution; if redistribution terms are unresolved, ship download/ingest instructions rather than silently bundling source data in a public repository.

**Done when:** the inspected aviation import yields 6,169 records and 5,122 distinct pairs; facility import yields 200 records; source lookups reproduce raw fields exactly and old corpus versions remain retrievable.

### P1.3 — Build and measure the hybrid engine

1. Precompute normalized BGE embeddings in a versioned offline command. Resolve model commit, dimensionality, normalization, token/prefix settings and document-text hashes. Store embeddings with corpus/model/revision/representation. Fail readiness for mismatch or missing required index artifacts.
2. Build immutable in-process raw/normalized BM25 indexes per corpus/domain. Query dense exact cosine and both lexical branches, collect at most 50 candidates each, merge IDs using proposed RRF and compatibility tiers. Do not port FTS under a BM25 name.
3. Implement explicit component/symptom/number/location/laterality/negation compatibility and source-span explanations. Preserve unknown separately from mismatch; no model filter pretending unknown records match the selected aircraft. Keep normal fault retrieval centered on PROBLEM.
4. Duplicate-aware selection returns representatives plus members/counts. Supply up to six useful original records for synthesis; preserve relevant differing findings. Add record fetch batching and retrieval timings. Lexical zero scores return no lexical hits; technical failure is typed separately from zero hits.
5. Implement read-only search/record API routers using the same service used by P2 tools. Scope every corpus/evidence fetch. No arbitrary SQL or broad public admin route.
6. Implement deterministic `compare`, `patterns`, `sensitivity` services. Sensitivity changes at most three single dimensions, freezes other versions/filters, computes rank/set deltas and produces verifiable result manifests. Pattern counts state raw rows versus unique pairs and exact corpus/filter scope. P2 stores run-bound receipts; both agree the immutable computation interface before coding.
7. Add constrained query expansion/rewrite and facility as official stretches after the first real vertical slice. Optional cross-encoder ranks at most 20 compatible pairs; retain only after measured gain. No model training/stacking based on 15 queries.

**Handoff:** real service implementations, corpus/model/index versions, exact record snapshots, compatibility facts/spans, receipt payloads/manifests, feature availability and degraded/error cases. P2 handles search-run persistence and evidence snapshot IDs; do not build a second session repository in retrieval.

### P1.4 — Compose, deploy, evaluate and integrate

1. Mount P2's workflow router; supply DB/auth/settings/services and lifecycle hooks. Fail readiness until required source/schema/models are usable. Model download is a build/startup dependency, not a surprise first-query task. Test available host memory rather than assuming a free tier can load models.
2. Configure development and production API/database/signing secrets outside Git. Give P2 development access without sharing the production DB unnecessarily. Record non-secret provider/model/deploy metadata only. Use managed DB TLS and persistent volumes/backup appropriate to the chosen host.
3. Package static assets, prompt, schema/index metadata and fixed model revisions. Configure HTTPS, same-origin, host port and streaming timeouts/buffering. P2 validates browser behavior; you own deployment configuration and rollback/runbook. Preserve source attribution and dependency/license notes.
4. Author development and held-out positive/hard-negative labels; freeze evaluation before tuning. Integrate P2's refusal set. Run raw BM25, dense-only, hybrid, compatibility/grouping and optional reranker/rewrite ablations, with denominators, timings, versions and limitations. Human claim checks are P2-led; do not substitute exact-span checks for semantic citation precision.
5. Merge small reviewed P2 changes, run joint contract/integration checks, deploy the frozen build, and record the actual URL only after fresh-browser acceptance. Supply runbook and measured results to P2's demo/deck. Review P2's claim/mode/history behavior while P2 reviews your source/ranking/metrics.

## Reuse map for your side

| Immutable source file | Adapt into | Preserve / change |
|---|---|---|
| `pipeline/fusion.py` | `maintenance/retrieval/fusion.py` | RRF mechanics; namespaced record keys and new weights |
| `pipeline/embedder.py` | `maintenance/models/embedding.py` | Provider/local inference abstraction; fixed BGE 384 revision, normalized vectors |
| `pipeline/reranker.py` | `maintenance/models/reranker.py` | Bounded batched inference; exact MiniLM model ID and score caveats |
| `pipeline/database.py` | `maintenance/db.py` | Pool lifecycle; small pool and exact cosine baseline |
| `pipeline/search.py`, `retrieve_dense.py`, `retrieve_bm25.py` | New retrieval service modules | Stage separation, diagnostics; replace recruiter filters and FTS default |
| `db/migrations/010,014,016` | New maintenance migrations | Structural ideas only; new tables, actual BM25 outside DB |
| `pipeline/observability.py` | `maintenance/telemetry.py` | Optional timing/traces, with private content redacted |

The active source orchestrator is more developed than its README; do not reconstruct search from the old README alone. Do not reuse salary/location/experience relevance, candidate IDs, implicit recruiter preference learning, arbitrary query tools or silent auto-relaxation. RRF/reranking measure relevance, not diagnostic correctness. Amazon 2026 is inspiration for staged candidate recall and bounded costly matching; exact winner channels/code were not recovered.

## How you depend on person two

P2 must give you schema requirements, provider smoke evidence, route aggregator, component catalog IDs and lifecycle hooks early. They also supply validated answer/event fixtures and browser feedback. Your catalog consumers must pin their reviewed catalog version. Their repository must use your DB/auth interfaces; yours must not assume an answer shape different from the frozen contracts.

When blocked on P2's provider/UI, continue ingest/retrieval/fixtures/evaluation. When they are blocked on your real engine, provide fake implementations, record fixture shapes and a clear handoff commit. Do not wait for both halves to be finished to integrate: the first positive and refusal flow is the H2 goal.

## Your final handoff checklist

- [ ] Reproducible migration/ingest/index commands and known source/version counts.
- [ ] Tested service interfaces, source spans/hashes and receipts matching contracts.
- [ ] True BM25 and dense branches observable on a normal query.
- [ ] Corpus/model/pipeline/cache invalidation and failures tested.
- [ ] Dependency lock and P2 provider smoke result tied to a commit.
- [ ] Deployment readiness, persistent storage, secret configuration and runbook.
- [ ] Held-out retrieval/ablation report with actual denominators and timings.
- [ ] Joint E2E evidence, remaining feature limitations and source/data-rights notes.

## Starter prompt for person one

```text
You are person one implementing Maintenance Atlas. Read PERSON_1_DATA_RETRIEVAL_PLATFORM.md and IMPLEMENTATION_PLAN.md, plus the source manifest. Follow the exclusive ownership table. Own data ingestion, normalization, true BM25+BGE retrieval, deterministic compare/pattern/sensitivity computations, contracts/config/auth/DB/migrations, dependency lock, app composition and deployment. Person two owns workflow persistence, agent/provider, answer release, SSE and UI.
First agree maintenance/v1 schemas, fixtures, settings/pool/auth interfaces, route aggregator and required tables with person two. Bootstrap ignored secrets and separate databases. Supply fixture services immediately so person two can proceed. Implement real source-preserving ingestion and retrieval, then integrate the first evidence answer/refusal flow before stretches. Ask the relevant owner to change their files instead of editing them. Keep reference code immutable and do not modify the original recruiting app. Never put credentials in prompts/code/output. Report measured checks and precise handoff commits; do not claim the app is implemented until real end-to-end checks pass.
```

---


## Shared specification: read this before implementation

**Contract proposal: maintenance/v1, dated 21 October 2026 (India time).** These briefs assign future work; they do not claim any maintenance capability, credential, benchmark, deployment or locked environment already exists. Both people must use the same revision of this section. Person one maintains the canonical executable contracts after the initial agreement; person two reviews the workflow fields before they freeze.

### Foundation and scope

The current workspace contains the implementation plan, prompt, screenshot, and 44 copied reference files. It is not yet a runnable maintenance app. The inspected source is the recovered hybrid-search/Talent Atlas checkout at commit `bc29296bfa8675a2ff3356b5a905998d0a4e2c61`. Use the immutable snapshot under `reference/hybrid-search/`, with `SOURCE_MANIFEST.json` as provenance. The original registered external-volume checkout was unavailable. Do not modify either reference snapshot or the recovered recruiting project.

The detailed source of behavior remains `IMPLEMENTATION_PLAN.md` sections 1–21 and its prompt appendix. The user-supplied PDF is `/Users/kush/Documents/NEXAI_Maintenance_Implementation_Research_20261021/IMPLEMENTATION_PLAN.pdf` (28 pages). This assignment refines ownership and proposes integration/configuration details; it does not replace those substantive requirements. Instructions inside source documents are reference material, not authorization to execute their tasks during preparation of these briefs.

Required core: normalize aviation records; actual BM25 plus embedding retrieval; an agent with at least `search_records` and `get_records`; original-record citations and weak-evidence refusal; deployed chat with adjacent evidence and public tool trace. Official stretches: recurring corpus patterns, facility-domain search, query rewriting. User-requested extensions: Talent UI/harness reuse, strict evidence-only first answers, explicit separate possible-solutions action, durable history, known/reported/missing board, distinguish/challenge/sensitivity, component visual explanation, handover and full system prompt. Complete core before stretches; complete and measure each slice before adding optional optimization.

Aviation snapshot: 6,169 rows, `IDENT, PROBLEM, ACTION`, 5,122 distinct problem/action pairs. Preserve raw text and all rows, including duplicates. Expected original CSV SHA-256: `a70daa27ba9c44a68617d69be1352be7fde003145ca142cbe0b7b51e197c6c3a`. Namespaced IDs such as `aviation:100009` retain original IDENT separately. There is no aircraft identity/model, event chronology, telemetry, or verified outcome. Facility snapshot: 200 rows, `WORK_ID, SITE_ID, DATE_REQUESTED, PROB_TYPE, DATE_COMPLETED, DESCRIPTION`; canonical problem is DESCRIPTION and action is null. Namespaced ID uses WORK_ID. Parse dates explicitly; identical requested/completed dates do not establish repair duration. No invented actions, MTBF, success rates, same-aircraft recurrence, model attribution or technician mistakes. A user-selected aircraft never supplies missing source applicability.

### Stack and version policy

| Layer | Chosen stack | Ownership / qualification |
|---|---|---|
| Runtime | Python 3.11; Docker | P1 pins image and dependencies after smoke tests |
| API / validation | FastAPI, Uvicorn, Pydantic 2, pydantic-settings | Same-origin API/static service |
| Agent | Existing PydanticAI 1.x integration; initial range `>=1.106.0,<2.0` | P2 ports harness; P1 commits tested lock |
| Provider transport | OpenAI-compatible Chat Completions via OpenAI SDK / PydanticAI adapter | Direct DeepSeek API, not a ChatGPT/Codex login |
| Default generation | `deepseek-flash`, explicit non-thinking mode | Account access and full adapter round trip still untested |
| Database | PostgreSQL 17 + pgvector, asyncpg | Exact cosine search first, persistent storage |
| Lexical retrieval | `rank_bm25.BM25Okapi` | Real BM25, not PostgreSQL `ts_rank_cd` |
| Embeddings | Sentence Transformers, `BAAI/bge-small-en-v1.5`, 384 dimensions, normalized | Local inference; fixed artifact revision and query prefix in manifest |
| Optional reranker | `cross-encoder/ms-marco-MiniLM-L6-v2` | Local bounded inference; fixed revision, evaluate before enabling |
| Frontend | Adapted HTML/CSS/vanilla JavaScript, fetch, SSE, SVG | Preserve Talent design and interactions; no React/Next rewrite |
| Tests | pytest, pytest-asyncio, HTTP/API tests and real-browser checks | Separate ownership below |
| Uploads | python-multipart; PDF text extractor such as pypdf | TXT/MD/PDF, bounded and untrusted |
| Hosting | One Docker API/static service + durable compatible PostgreSQL | Provider not yet selected; no claimed public URL |
| Observability | Redacted JSON timings; optional Langfuse | Off by default; never required to answer |

Add `pydantic-ai-slim[openai]` for the selected transport. The copied source declares a Groq extra; copying it unchanged is not a DeepSeek setup. Other core packages are `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `asyncpg`, `pgvector`, `openai`, `httpx`, `sentence-transformers`, `rank-bm25`, `python-multipart`, the chosen PDF extractor, and development test/lint packages. Exact resolved versions and model commit hashes must be generated and tested, not guessed here. Do not copy unused recruiter dependencies wholesale. No Redis, ParadeDB, Supabase, Qdrant, Pinecone, paid embedding API, graph DB, LangChain or new frontend framework is needed for this architecture. Additional services require an explicit measured reason and contract update.

### Credentials, accounts and configuration

**Required external AI secret: `DEEPSEEK_API_KEY`.** Also provide database credentials and an application signing secret. Neither person needs to paste a key into these documents, a prompt, Git, browser settings or frontend code. The following names are the proposed maintenance settings interface, not a claim about already implemented environment variables.

| Variable | Required? | Purpose / provisioning | Responsible person |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | Yes for live agent | Create separate development keys in the team's DeepSeek API account; configure deployment key in host secret store | P1 provisions production; P2 uses own dev key |
| `DEEPSEEK_BASE_URL` | Yes, non-secret | `https://api.deepseek.com`; server-only approved endpoint | P1 settings; P2 adapter |
| `DEEPSEEK_MODEL` | Yes, non-secret | `deepseek-flash`; allowlist and real capability smoke test | P1 config, P2 verifies |
| `DATABASE_URL` | Yes, secret | `postgresql://USER:PASSWORD@HOST:5432/maintenance`; asyncpg-compatible DSN, TLS for remote host | P1; each dev gets a separate database |
| `SESSION_SIGNING_SECRET` | Yes, secret | Random 32+ byte secret; signs server-issued anonymous owner cookie | P1 provisions; P2 consumes auth dependency |
| `APP_ENV`, `APP_ORIGIN`, `PORT` | Yes, non-secret | development/production, exact browser origin, host port | P1; browser stays same-origin |
| `EMBEDDING_MODEL`, `EMBEDDING_DIM` | Yes, non-secret | BGE model above, `384` | P1 |
| `EMBEDDING_REVISION`, `MODEL_CACHE_DIR` | Before release | Resolved artifact commit, readable packaged cache; fail readiness on mismatch | P1 |
| `RERANK_ENABLED`, `RERANK_MODEL`, `RERANK_REVISION` | Optional | Default false; MiniLM above if measured useful | P1 |
| `LANGFUSE_ENABLED` | Optional | Default false | P1 |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` | Only if tracing enabled | Optional project credentials/endpoint; redact content first | P1 |
| `HF_TOKEN` | Usually unnecessary | Public models can be downloaded without it; optional authenticated download/rate limits | P1 build environment only |
| Host/registry access or deploy token | Deployment only | Depends on chosen host; use team access/host CLI, not an app variable or model tool | P1 |
| Git repository access | Collaboration only | Each developer's own authorized account/SSH credential | Both |

OpenAI/Groq/Gemini API keys are not required for the selected default. They are legacy/provider alternatives in the reference project, not new requirements. ChatGPT Plus/Pro, Codex, Antigravity and a browser chat subscription do not provision the DeepSeek application API credential. Set spending limits and inspect actual usage rather than assuming subscription coverage. There is no verified key/account balance in this audit; no existing secret files were inspected.

Proposed `.env.example` skeleton, all values placeholders or non-secrets:

```dotenv
APP_ENV=development
APP_ORIGIN=http://localhost:8000
PORT=8000
DATABASE_URL=postgresql://maintenance_dev:REPLACE_ME@localhost:5432/maintenance_p1
SESSION_SIGNING_SECRET=REPLACE_WITH_RANDOM_SECRET
DEEPSEEK_API_KEY=REPLACE_WITH_DEV_KEY
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIM=384
EMBEDDING_REVISION=REPLACE_WITH_RESOLVED_MODEL_COMMIT
MODEL_CACHE_DIR=/app/models
RERANK_ENABLED=false
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L6-v2
RERANK_REVISION=
LANGFUSE_ENABLED=false
```

P2 uses another local database name, e.g. `maintenance_p2`, and a local cache path. Use a unique Compose project name and host port per developer when sharing one machine. Missing/placeholder required settings must fail readiness clearly. Commit only `.env.example`; ignore `.env*` except that example, local datasets, caches, uploads and private transcripts. Never print DSNs or secret values in health, errors, logs, tool arguments or public traces. Use secure HttpOnly SameSite cookies in production and Origin/CSRF checks on mutations. API keys are never sent to the LLM as context.

Provider details checked on 21 October 2026: official DeepSeek tool examples use the endpoint/model above and `extra_body={"thinking":{"type":"disabled"}}`. P2 must map that through the pinned PydanticAI version. Do not assume a native strict JSON-schema output mode merely because JSON-object output works. Use supported tool-based structured output or JSON-object output plus Pydantic validation after testing. Keep strict beta endpoint behavior out of the baseline. Preserve actual model tool-call/result IDs; deterministic prefetch belongs in context, not fabricated Chat Completions tool exchanges.

Sources: [DeepSeek tool calls](https://api-docs.deepseek.com/guides/tool_calls/), [thinking settings](https://api-docs.deepseek.com/guides/thinking_mode/), [JSON output](https://api-docs.deepseek.com/guides/json_mode/), [PydanticAI OpenAI transport installation](https://github.com/pydantic/pydantic-ai/blob/main/docs/install.md), [BGE model card](https://huggingface.co/BAAI/bge-small-en-v1.5). Documentation supports API mechanisms; it does not establish this app's account access or compatibility.

### Exclusive file ownership

P1 means person one; P2 means person two. Paths below are repository-relative proposed files. New shared files require a named owner before editing. Both people may read everything.

| Owner | Exclusive write area |
|---|---|
| P1 | `maintenance/{config,contracts,db,auth,telemetry}.py`; `maintenance/models/{embedding,reranker}.py`; all `maintenance/ingest/` and `maintenance/retrieval/` |
| P1 | `maintenance/features/{compare,sensitivity,patterns}.py`; `api/main.py`; `api/routes/{search,records}.py` |
| P1 | All `db/migrations/`; `config/{abbreviations,calibration}.json`; all `contracts/` schemas, fixtures and interface examples |
| P1 | `scripts/{ingest,build_indexes,verify_dataset,evaluate}.py`; `eval/{development,heldout,hard_negatives}.jsonl` |
| P1 | `pyproject.toml`, `requirements.lock`, Dockerfile, compose.yaml, `.env.example`, `.gitignore`, root README, deployment/CI files, root `DEV_LOG.md` |
| P1 | `tests/data/`, `tests/retrieval/`, `tests/contracts/`, `tests/integration/`; `docs/p1/` |
| P2 | `maintenance/{agent,agent_run,tools,events,session_repository,context,board,hypotheses,answer_validation,answer_rendering,attachments}.py`; `maintenance/models/provider.py` |
| P2 | `maintenance/features/{challenge,handover,visuals}.py`; `api/routes/{workflows,sessions,runs,actions,uploads,visuals,observations,feedback,pins}.py` |
| P2 | All new `api/static/maintenance.*`, API client/panel JS, reviewed visual assets; `config/{component_catalog,visual_mappings}.json` |
| P2 | `docs/prompts/maintenance_system_prompt.md`; `scripts/provider_smoke.py`; `eval/refusal.jsonl`; `tests/agent/`, `tests/workflows/`, `tests/ui/`; `docs/p2/` and demo/deck sources there |
| Immutable | `reference/`, original implementation plan, source PDFs and original datasets |

P1 owns package `__init__.py` files during bootstrap; create empty ones so neither person needs to modify a package export file later. Use direct module imports. P1's `api/main.py` mounts P1 routers and **one P2-owned `api.routes.workflows.router` aggregator**. P2 mounts all their subrouters inside that file; neither edits the other's mounting file. Health/capabilities live in P1's composition layer and query P2's explicit readiness interface. P1 declares settings; P2 requests additional fields instead of silently reading unrelated environment names.

All migrations belong to P1, including the session/evidence/visual tables used by P2. P2 owns the workflow repository SQL, not schema changes. P2 supplies schema requirements in `docs/p2/schema-requests.md`; P1 delivers numbered migrations. No competing Alembic history, ad hoc CREATE TABLE at runtime, or editing already applied migrations. P2 writes their own progress log; P1 incorporates summaries into root documentation.

### Contract-first integration

Before parallel feature implementation, agree and commit `contracts/v1/` JSON schemas, wire examples, typed interfaces and synthetic fixtures. P1 authors; P2 reviews. The brief specifies fields semantically; those executable schemas must close optionality/enums before coding. Mark every fixture `fixture_only=true`; fixtures never count as real evidence or measured results.

Minimum models: `SearchSpec`, `SearchResult`, `RecordSnapshot`, `EvidenceSpan`, receipt union, `DraftAnswer`, `AnswerEnvelope`, `HypothesisEnvelope`, `PublicEvent`, `SessionSnapshot`, `BoardItem`, `ComponentContextEnvelope`, action request/error models. Use Pydantic strict validation and reject unknown request fields. UUIDs for app entities, `domain:source_id` for source records. Source citations always include corpus version. Cross-module imports must not form a cycle: contracts/config/db at the bottom; retrieval and workflow services above; API composition at the top.

P1 provides `SearchService.search(spec, scope)`, `RecordService.fetch(record_ids, scope)`, `PatternService.summarize(filters, scope)`, `ComparisonService.compare(record_ids, scope)`, `SensitivityService.compare_specs(base_spec, variants, scope)` as proposed async interfaces. `scope` is server-created authorized owner/session/run/corpus context. Search returns versioned results; P2 persists the search run and asks P1's computation services for reproducible receipts. P1 computes source-derived facts; P2 stores immutable run-bound receipts and enforces release/ownership. Both agree receipt IDs/hash semantics before implementation. No raw browser SQL, provider URL or arbitrary filesystem argument is allowed.

`SearchSpec` carries raw/normalized query, domain, corpus IDs, intent, component/symptom/location/number mentions with original spans, negation, ambiguous terms, requested fact type, profile revision and filters. `SearchResult` carries query/spec, corpus/index/model/pipeline versions, ordered namespaced IDs, per-channel ranks/scores, compatibility tiers with source spans, duplicate groups, timings, degraded-branch status and limitations. A successful zero-hit search is distinct from a service failure. P2 must not infer answerability from a score alone.

`RecordSnapshot` includes corpus ID, record/source ID, original fields, raw problem/action, source hash, normalizer version, flags and source-model applicability. P2 allocates run-bound evidence snapshot IDs while retaining P1's exact source identity. A log-span support includes `evidence_id, record_id, field, start, end, quote, source_sha256`; offsets are half-open Python Unicode code-point indices into the raw field. Gate checks the exact raw substring and hash; JS uses `Array.from(text)` or tested offset conversion. Hash names must unambiguously identify file versus field hashes in the executable schema. Aggregate and search-comparison claims require server computation receipts, never LLM-estimated numbers.

`AnswerEnvelope` includes IDs, server mode, validated status, atomic supported claims, limitations/gaps/clarification references, allowlisted visual refs and server-computed actions. Status enum: `supported_historical`, `partial_evidence`, `clarification_needed`, `insufficient_evidence`, `retrieval_unavailable`. An API failure must not become a claim that the database contains no relevant case. The model draft cannot authorize modes, IDs, state revisions, validation success or available buttons.

P2 supplies `WorkflowService`/router interfaces to P1 plus startup/shutdown readiness hooks. P1 supplies an initialized DB pool, validated settings, owner dependency and retrieval service through app state/dependencies. P2 owns session persistence, run orchestration and events. Services must be dependency-injectable; do not import and run the reference `pipeline` package.

### Concrete request examples for the contract review

Illustrations only; IDs below are placeholders and must be replaced by server-issued IDs. P1 and P2 must freeze exact wire optionality in the executable schemas at H0.

Message creation body (the route, not the browser, selects EVIDENCE):

```json
{"text":"Cylinder #2 intake leaking. Show similar historical records.","idempotency_key":"11111111-1111-4111-8111-111111111111","expected_revision":3}
```

Action creation body:

```json
{"action":"hypothesis","parent_answer_id":"22222222-2222-4222-8222-222222222222","expected_revision":4,"idempotency_key":"33333333-3333-4333-8333-333333333333","parameters":{}}
```

The server checks the stored parent/hash and authorization, then records the resulting run's authoritative `state_revision`; browser revisions never grant authority. Exact action enum spelling and parameter variants are part of the H0 contract. Creation responses include session/run IDs, accepted revision and the event subscription URL. Session snapshots include `state_revision`, board/profile, ordered messages, released answers, active run and source-version references. Capabilities must declare unavailable actions rather than letting the browser assume support.

Public event illustration:

```json
{"protocol_version":"maintenance/v1","run_id":"44444444-4444-4444-8444-444444444444","sequence":7,"type":"validation_started","created_at":"2026-10-21T17:30:00Z","data":{"fixture_only":true}}
```

Proposed upload limits: 5 MB/file and an explicit extracted-text cap agreed at H0; reject unsupported MIME, encrypted or non-text PDFs with a clear status. P1 adds settings for run/tool/model/search deadlines, upload/text caps, pool/semaphore limits, model allowlist and feature flags; P2 consumes them through validated settings. Do not introduce a second hidden settings source. Default optional reranking/tracing to disabled until tested; capabilities and UI must follow actual readiness.

### HTTP and streaming contract

Product route `/maintenance`; API prefix `/api/maintenance/v1`. Body schemas and exact responses live in the frozen contract package. All private entities are owner-scoped by a signed/authenticated server identity, not a user-supplied owner UUID.

| Routes beneath API prefix | Owner / behavior |
|---|---|
| `GET /health`, `GET /capabilities` | P1 composition; readiness, domains, versions, allowlisted models/features; no secrets |
| `POST /search`, `GET /records/{domain}/{source_id}?corpus_id=...` | P1; same retrieval core and immutable source lookup |
| `POST, GET /sessions`; `GET, PATCH, DELETE /sessions/{id}` | P2; create/list/restore, revision-checked profile/rename/archive, explicit owned deletion |
| `POST /sessions/{id}/messages` | P2; text, UUID idempotency key, expected revision; EVIDENCE only; returns run ID |
| `GET /runs/{id}/events?after=N`; `POST /runs/{id}/cancel` | P2; owner-authorized durable replay and cancellation |
| `POST /sessions/{id}/actions` | P2; typed action, parent answer, state revision, idempotency; server authorization |
| `POST /sessions/{id}/observations`, `/attachments`; `POST /answers/{id}/feedback` | P2; explicit user input with provenance; never trusted automatically |
| `GET /visuals/{asset_id}`, `/components/{component_id}/context` | P2; reviewed allowlisted asset/knowledge/applicability |
| `PUT, DELETE /sessions/{id}/pins/{domain}/{source_id}` | P2; version-preserving pins and revision checks |
| `GET /sessions/{id}/handover` | P2; source-labeled Markdown, hypotheses excluded by default |

One live run per session. A stale revision/concurrent conflicting request returns 409; same idempotency key and same payload returns existing run, changed payload returns 409. Private missing/foreign resources must not disclose existence. Explicitly distinguish validation errors, unauthorized access, not-ready dependencies, rate limits and provider timeouts in a typed error envelope. Choose and freeze exact status codes in contracts.

Every SSE event has `protocol_version=maintenance/v1`, `run_id`, monotonic `sequence`, `type`, UTC `created_at`, `data`; SSE `id` equals sequence in that run. Persist before emit. GET subscription never starts new inference. Replay after cursor, de-duplicate by run/sequence, hydrate from server after reload. Public event types: `run_started`, `query_interpreted`, `search_started`, `search_completed`, `tool_started`, `tool_completed`, `evidence_ready`, `validation_started`, `board_updated`, `answer_validated`, `run_cancelled`, `run_failed`, `done`. No public reasoning, draft text deltas or rejected answers. Use roughly 15-second comment heartbeats, disabled proxy buffering and tested reconnect behavior. Cancellation and failure retain earlier validated answers.

### Retrieval, evidence and operational limits

Baseline: raw BM25 + normalized BM25 + exact cosine BGE retrieval, up to 50 candidates each. Start weighted RRF with rank constant 60, weights 0.5/0.5/1.0; these are unmeasured design defaults. Rank within explicit compatibility tiers, not across an overlooked component/number/negation conflict. Default fault representation is PROBLEM; optional problem+action representation is separately versioned for explicit action/history queries. Never return arbitrary lexical hits when all BM25 scores are zero. Preserve negation, laterality, units and number context; `#2` is not automatically a cylinder. No silent filter relaxation. Group duplicate cards while preserving every source ID and raw/distinct counts. Up to six representative records; retain relevant alternative findings without forcing unrelated diversity. Rerank at most 20 compatible pairs if enabled; scores are not repair probabilities.

Default budgets to implement and measure: eight tool calls, three searches, four model requests plus one bounded validation repair, 10 records per fetch batch, six synthesis records, total run deadline 45 seconds. Start DB pool at 2–5 connections per instance and one concurrent CPU rerank batch; run inference off event loop. Version/cache by complete query/spec, domain/corpus, model/revision/prefix, normalizer and pipeline versions. Private context caches include owner/session/state. Prepackage model artifacts and verify RAM/cold-start/streaming on the selected host.

The first answer and normal follow-ups use evidence-only mode. Fetch original records, generate structured draft, validate authorized spans/receipts and semantic support, repair once, then use extractive fallback or explicit insufficient evidence. Never release the draft. A matching quote does not by itself validate a causal paraphrase; assess entailment and reject uncertain support. Start with deterministic historical wording before enabling free paraphrase. 'Action recorded' does not mean 'repair succeeded'. Headline, gaps and clarifications must not provide an uncited escape hatch.

Only an explicit click on **Possible solutions — unverified** authorizes HYPOTHESIS, bound to released parent/current state/owner/idempotency. Separate envelope, storage and visible label. No speculative leakage into first answer, board facts or later trusted context. Conceptual explanations are permitted in that branch; fabricated model-specific repair procedures/specifications are not. CHALLENGE, DISTINGUISH and SENSITIVITY remain evidence-only. Handover preserves provenance and excludes hypotheses by default.

### Dependency handoffs and conflict prevention

| Checkpoint | P1 delivers to P2 | P2 delivers to P1 | Dependency / acceptance |
|---|---|---|---|
| H0: contract/bootstrap | Layout, ownership, DB/auth/config interfaces, schema/fixture draft, dependency manifest | Required workflow tables/fields, provider dependencies, visual component IDs | Joint review before feature branches; no incompatible independent schemas |
| H1: offline development | Fake implementations matching contracts, then ingest/retrieval/snapshot service | UI and agent tests using fixtures; schema requests; reviewed catalog revision | Both can work without the other's unfinished service; fake/live status visible |
| H2: first vertical slice | Real aviation search/get, pool/auth, migrations, API mounting, live provider env | Two-tool agent, evidence gate, session/message routes, SSE and adapted UI | Public-ready positive + refusal flow with real IDs; no fixture evidence |
| H3: persistence and scope | DB constraints/indexes, facility/rewrite/pattern services, versioned receipts | Restart-safe sessions/events, board/actions, facility selector, history restore | Replay, cancellation, two-owner isolation and revision/idempotency tests pass |
| H4: differentiation | Comparison/sensitivity computation and optional measured reranker | Challenge/hypothesis/handover, linked reviewed 2D panel and uploads | Buttons use real contracts; mode/applicability/source boundaries hold |
| H5: release | Locked build, fresh deploy, retrieval metrics/ablations, runbook | Browser/API evidence, human citation/refusal review, demo and deck sources | Both sign off checklist; report actual counts and remaining limitations |

P1 needs P2's component catalog early for annotation; freeze stable IDs and a catalog revision. P2 needs P1's normalized spans and mapping evidence for honest visual highlights. Unsupported model configurations remain generic/unknown. P1 needs provider smoke results before locking the build. P2 needs migrations before database integration; use fixtures to avoid blocking UI/harness work. Both need the other for end-to-end acceptance. Neither can independently declare the project complete.

Use separate clones/worktrees and branches, suggested `person-1-retrieval-platform` and `person-2-agent-experience`, from the same baseline. The workspace currently has no verified Git repository; P1 bootstraps or connects the agreed repository and sets `.gitignore` before committing. This document does not create/push a repo. Commit bootstrap/contracts first; then P1 merges small reviewed changes, and both rebase at checkpoints. Ownership prevents file collisions, not semantic incompatibility. Request changes to another owner's files through a small written schema/interface/dependency request; the owner implements it. Do not resolve conflicts by overwriting the other branch. Freeze contracts before final testing; change versions and fixtures together for breaking changes.

### Release gates and review evidence

Gate A: mandatory aviation hybrid search, two real tools, cited/refusing answer, deployed reused UI and trace. Gate B: all three official stretches. Gate C: durable investigation workflow, action separation, board and reviewed 2D illustration. Gate D: measured reranker/typos/3D/training simulator only after the prior gates. Use the earlier 22 October 2026 3:00 PM India deadline as planning cutoff pending organizer confirmation; the earlier documents reported conflicting 3:00/3:30 wording, not a confirmed schedule here.

P1 freezes at least 15 positive held-out query judgments and distinct development queries; P2 freezes at least five unsupported questions. Review acceptable record IDs and duplicate/query families before tuning. Relevant records stay searchable; held-out applies to queries/judgments, not deleting their evidence. P2 authors refusal fixtures before seeing results; P1's evaluator consumes them without changing labels to improve scores. Report Hit@5 as numerator/denominator, retrieval ablations, human semantic citation precision, deterministic span validity, correct/false refusals, unsupported claims, actual p50/p95 timings, token usage and tested history behavior. No promised accuracy figure is a result.

Failure tests: unavailable provider, DB loss, embedding/index mismatch, cancellation, duplicate request, stale state, cross-owner IDs, reconnect/restart, fake citation/quote/offset/hash, source prompt injection, hypothesis-to-evidence contamination, facility null ACTION, unsupported torque/model question, Unicode offsets and untrusted upload rendering. Persist lease ownership/expiry; an API restart must not steal a still-live worker's run. Deletion must not remove the immutable shared corpus.

Fresh production acceptance: HTTPS/same-origin; persistent DB; models preloaded; version-compatible schema/index; owner isolation; real positive and unsupported questions; citations reveal exact text; SSE reconnect creates no extra run; reload/restart preserves evidence/board/modes; cancellation works; no secret in HTML/network payload/logs. Keep results in owner-specific docs. No claim of a working feature until its real acceptance check passes. Final submission/publication remains a team action unless separately authorized.

### Source trail

- `IMPLEMENTATION_PLAN.md`, especially sections 2–3 (reuse/stack), 4–6 (data/search), 8–15 (answers/harness/API/history/visual/UI), 17–21 (tasks/evaluation/release).
- `docs/prompts/maintenance_system_prompt.md`; `docs/assets/talent-atlas-reference.png`.
- `reference/hybrid-search/SOURCE_MANIFEST.json`, copied pyproject and pipeline/UI files; original source defaults are not maintenance defaults.
- Earlier project chats reviewed: **Investigate MaintNet datasets (2)** and **Investigate MaintNet datasets**. **Compare Idea Fit** and **Cross Encoders Allowed** exposed user messages with incomplete assistant/image content; no missing answer or image conclusion is assumed. Cross-encoder is an optional plan component, not asserted organizer approval from that inaccessible image.
- Original research sources remain under `/Users/kush/Documents/NEXAI_Maintenance_Research_20261021/`, including raw CSVs, dataset profiles, research report, and organizer PDFs. Shared ownership/repository paths/env names above are concrete proposals added by these briefs.
