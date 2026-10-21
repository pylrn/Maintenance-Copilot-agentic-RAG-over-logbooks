# Person two integration handoff

Development checkout: `/Volumes/MAC/Projects_devolopment/nexai_implimentation`, branch `person-1-retrieval-platform`. Source planning folder: `/Users/kush/Documents/ChatGPT/maintainence copilot`. Canonical remote: `https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks.git`. Person-one commits use `person-1-retrieval-platform`; coordinate integration through its pull request. Use this implementation checkout as your baseline; the planning folder has no app code. Use a separate checkout/branch for concurrent editing. Read `docs/work-split/PERSON_2_AGENT_UI_WORKFLOWS.md` for full assignment and the ready-to-paste prompt.

## Available now

- `maintenance/contracts.py`: typed shared request/search/source/answer/hypothesis/board/session/component/event/receipt models. `contracts/v1/schema.json` and marked fixtures are exported from it. This is the proposed integration baseline; your schema review is still required. Send requested changes to P1 rather than editing shared contracts/migrations/config/lock.
- `RetrievalEngine.search(spec, scope)` returns SearchResult. Input normalized text/mentions are rederived from raw query rather than trusted from the client. `spec.intent='fault'` uses problem-only embeddings/lexical text; `action_history` uses separately built problem+action representation. Record IDs are namespaced and corpus IDs explicit. Scope is constructed server-side.
- `RecordService.fetch(record_ids, scope)` supplies original RecordSnapshots through PostgreSQL, including inactive corpus versions. Source IDs ambiguous across two authorized versions require a narrower corpus scope. No session writes happen inside these services.
- `PatternService.summarize(filters, scope)`, `ComparisonService.compare(record_ids, scope)` and `SensitivityService.compare_specs(base_spec, variants, scope)` return reproducible ComputationReceipt payloads. These have no trusted receipt UUID until you persist them under the current authorized run. Receipt manifest hashes cover scope, inputs, contributing source IDs/hashes and computed results.
- Schema tables exist for sessions/runs/messages/events/searches/answers/supports, tool exchanges, snapshots, hypotheses, receipts, summaries, attachments, feedback, pins, components and knowledge assets. P1 owns migrations; you implement repositories/transactions using them. No workflow repository or agent has been implemented by P1.
- `maintenance.auth.require_owner` is the FastAPI signed identity dependency; `require_session_owner(pool, session_id, owner_id)` makes a non-disclosing owned lookup. Signer comes from server settings. Pass owner scope explicitly; an incoming UUID is not authorization.

## Composition interface — use exactly this seam

Create your assigned `api/routes/workflows.py` with `router = APIRouter()`. Route paths there are relative to `/api/maintenance/v1`, which P1 mounts once. Include your sessions/runs/actions/etc subrouters inside it. Do not edit `api/main.py` or create a separate application. Restart the API after adding your module/static directory.

Optionally expose async `startup(app)` and `shutdown(app)` in that module. P1 calls them inside the application lifespan. At startup the following attributes are available:

```python
app.state.settings            # validated Settings; secrets are SecretStr
app.state.db                  # Database object, or None if unconfigured
app.state.pool                # asyncpg pool, or None
app.state.identity_signer     # IdentitySigner
app.state.search_engine       # RetrievalEngine, or None if unavailable
app.state.record_service      # RecordService (DB authority), or fixture engine in tests
app.state.pattern_service     # PatternService, or None
app.state.comparison_service  # ComparisonService, or None
app.state.sensitivity_service # SensitivityService, or None
app.state.workflows_ready     # False until your own checks succeed
```

Do not start an agent if DB/schema/index is unavailable. Declare your workflow readiness only after your lifecycle/worker setup passes; P1's health currently reports platform readiness and workflow readiness separately. Request a P1 capabilities update when real modes/visuals/model smoke checks are implemented; current `enabled_modes=[]` and `visuals_available=False` are deliberately honest placeholders.

`app.state.settings.deepseek_api_key` is currently absent in the local environment; create your own dev API key and configure it server-side. Do not reuse unrelated project credentials. PydanticAI `1.107.9` with the OpenAI transport is resolved; actual provider/tool/structured-output compatibility remains your smoke-test responsibility. Use `extra_body={"thinking":{"type":"disabled"}}` through the supported pinned adapter. No provider call has been made or charged by P1.

The local DB/signing values are in ignored `.env` (mode 0600), not in this handoff. On a separate machine, create your own settings/DB. Never copy the production signing key to a personal environment. Missing app signing secret in development uses an ephemeral identity key with no restart guarantee; configure a stable secret for history tests. Production settings fail without required secrets/HTTPS/model pin.

## Data and source interpretation

Active aviation corpus: `2795c1d6-a5f4-5c8d-a773-4ac724d10e99`, 6,169 rows / 5,122 distinct raw problem-action pairs. Facility: `b5f9d886-1b2c-56cc-96fe-ae0488597043`, 200 rows / 190 distinct descriptions. Facility ACTION is null and must never be manufactured. Neither selected aircraft context nor component overlap upgrades source-model applicability.

`source_file_sha256` identifies the original CSV. `field_sha256[field]` identifies exact decoded raw text, UTF-8 encoded. Copy that field hash into citation `source_sha256`. Unicode offsets are half-open Python code points into the raw field; use `Array.from(text)` or tested DOM offset conversion. Raw text always remains the citation authority; normalization and internal tags are search annotations.

Truncation is flagged by a stated heuristic (long unpunctuated endings), not reconstructed. Reviewed visual component IDs are not present yet. Supply your stable catalog/revision early; P1's internal component tags are not a verified aircraft drawing or geometry mapping. Source snapshot `applicability='unknown'` is intentional.

## Search-result handling

All three baseline channels run on ordinary faults. Per-channel scores/ranks are explainable relevance signals, not diagnosis probabilities. Compatibility `direct/related/tangential` is heuristic; exclude tangential hits from synthesis unless separately justified, and do not call related cases exact faults. Evidence gate still needs claim support checks, requested-fact coverage, mode isolation and applicability checks. Exact source quote validity alone does not validate a paraphrase.

A duplicate representative carries member IDs and raw count. Counts must come from computation receipts; do not infer corpus prevalence by the number of retrieved cards. Search sensitivity permits only approved disclosed one-dimensional edits, at most three variants, with negation and all other settings frozen. Comparisons return original field spans, not an LLM verdict or maintenance procedure.

Use `SearchResult.search_id` when inserting `search_runs`. Persist the immutable SearchSpec, versions, channel ranks, results and timings under the current run. Allocate evidence snapshot UUIDs for fetched record/field pairs. Persist actual model tool-call/result exchanges with provider IDs. Never use fake tool messages or browser-supplied transcript authority.

## Synthetic/offline development

From repository root:

```python
from contracts.v1.fakes import FixtureSearchService
from maintenance.contracts import SearchSpec, ServiceScope
from uuid import uuid4
service = FixtureSearchService()
scope = ServiceScope(owner_id=uuid4(), corpus_ids=[c.manifest.corpus_id for c in service.corpora.values()])
result = await service.search(SearchSpec(query_raw='intake leak', domain='aviation'), scope)
assert result.fixture_only
```

Fixture outputs have synthetic DEMO IDs and must be visibly marked and rejected for final production evidence. Fixtures are for UI/service contract development; they do not demonstrate an actual provider, maintenance answer or tested safety gate.

## Your first integrated acceptance slice

1. Review/request contract/schema changes and give P1 provider smoke evidence/dependencies.
2. Implement two actual tool wrappers against injected search/record services.
3. Persist a real session/run/search/evidence packet and structured answer draft.
4. Validate exact identities/spans/hashes and semantic/mode support; buffer all output until commit.
5. Stream public events and the released envelope with durable replay.
6. Port the Talent UI from immutable reference files, original record drawer and refusal state.
7. Prove positive and unsupported questions on real sources; then add requested workflow/actions/visual features in the brief's order.

Do not report a complete copilot based solely on P1's platform health. Citation precision, refusal quality, hypothesis isolation, restart-safe full history, UI/browser checks, live provider capability and public deployment remain to be completed together. P1's retrieval evaluation is provisional engineering evidence, not your answer-quality benchmark.

## Known baseline limits to preserve in the UI

Compatibility extraction is conservative and incomplete (especially enumerated numbers, ambiguous abbreviations and mixed negation scopes). Source spans and unknown/difference markers are exposed for review; the heuristic is not a calibrated diagnostic classifier. Do not infer that an omitted mention is absent from the source. `RecordSnapshot`/raw drawer remains the authority. Baseline reranking is disabled and no reranker accuracy claim has been measured. Search caches and a global tracing service are intentionally absent until justified; the original UI/harness mechanics are available in the reference snapshot for your port.
