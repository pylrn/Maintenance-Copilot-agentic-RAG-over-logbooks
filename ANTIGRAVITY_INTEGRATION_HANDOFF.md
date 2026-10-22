# Antigravity handoff: integrate the latest Atlas UI with the live retrieval and workflow backend

**Snapshot date:** 22 October 2026, Asia/Kolkata. **Audience:** the next Antigravity implementation session on Kushaan's Mac.

This is an implementation handoff, not a declaration that the integration is complete. Source-inspected behavior, live-verified behavior, requirements and proposed changes are labelled separately. Read the pasteable implementation prompt at the end after reviewing the current-state and contract tables.

## Current State Summary

The canonical backend is running locally against Supabase with the full 6,369-record corpus and 12,738 vectors. The separate retrieval admin works at http://localhost:8000/retrieval-lab. Server-side sessions, evidence snapshots, claim validation, workflow routes, native provider tool-loop code and SSE persistence exist. The active `/maintenance` page is still the older UI. Newer modular frontend files were preserved from an earlier GitHub merge, but were deliberately not made the active product because their demo-shaped contracts do not match the backend.

The newest UI is on **`origin/person-2-agent-experience` at `caf2be389998ab9b062e9c591962197956a585c5`**, fetched directly during this audit. Use this branch, not just `main`. It contains the approved single-input flow, teal sidebar, 33 aircraft regions, six distinct wing cutaways and the frontend author's integration handover. Those newest changes are fetched and inspected, but **not merged into the canonical development branch by this documentation task**. Do not confuse fetching or previewing them with completing integration.

### Exact repository and merge state

| Item | Inspected state |
| --- | --- |
| Canonical checkout | `/Volumes/MAC/Projects_devolopment/nexai_implimentation` |
| Repository | https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks |
| Backend branch / baseline | `person-1-retrieval-platform` / `ecba0c7ff443ffe7da53a9aeab4b697785f96c6b` |
| Latest fetched UI branch | `person-2-agent-experience` / `caf2be389998ab9b062e9c591962197956a585c5` |
| Latest fetched main | `8d9daa06f7230c2f6ca5f1d31db703d1e70b9c3f` |
| Main already integrated into backend | Only the earlier `b66fe7a`, with merge ancestry recorded in `ed49a79` |
| Existing draft integration PR | https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks/pull/1 |
| Live product entry | `/maintenance` currently serves `api/static/maintenance.html` |
| New UI entry to integrate | `api/static/maintenance/index.html` from the latest UI branch |
| Retrieval admin entry | `/retrieval-lab`; preserve separately from the product UI |

UI branch commits inspected, in dependency order:

- `738100b`: component explorers and conditional oil-loss view.
- `248a695`: guided investigation flow and unified sidebar.
- `3e0f006`: one input, concise flow, contextual internal views and animation.
- `ca6fb67`: larger 33-region airframe and refined wing mapping.
- `654c1dc`: six separate wing internal diagrams and parts lists.
- `caf2be3`: current project context and `INTEGRATION_HANDOVER.md`.

Main stops before the last four of these UI commits. Earlier onboarding descriptions of 20 segments, fabricated sensor-style displays, Windows-only setup, unfinished Supabase work, or a fully completed PydanticAI harness are not the present canonical state.

## Important Context

1. **Use the latest Person Two branch as the UI design authority.** Preserve its single composer for initial questions and follow-ups. Do not restore duplicate hero inputs, sample-card sections the user removed, or an older visual design from the original plan.
2. **The plan is a specification; code is implementation evidence.** The user-specified plan is `/Users/kush/Documents/ChatGPT/maintainence copilot/IMPLEMENTATION_PLAN.md`. Its only difference from the repository copy at this snapshot is a leading link to an older integrated-code handoff. The substantive specification is the same. Latest explicit user-approved UI choices override older palette/sample-card presentation requirements, not evidence or ownership invariants.
3. **The frontend handover is valuable but locally scoped.** Its statements that workflow files are absent and Supabase is unfinished describe Vansh's checkout. Those files and the connected database now exist here. Its API mismatch table and warnings about demo data remain relevant.
4. **No secrets belong in this document, browser bundle or Git.** Existing ignored private profiles hold configuration. Never print full environment files, DSNs, cookies, provider keys or rendered Compose configuration.
5. **Generation is currently extractive.** Live capabilities report `provider_configured: false`; configured model names are an allowlist, not proof of live inference. A Gemini credential was saved privately, but earlier chat-generation attempts timed out; do not claim a successful provider run. Retrieval needs no external embedding API key.
6. **Do more implementation before more testing.** The user explicitly wants fewer repetitive test runs. Implement a meaningful slice, run targeted checks and a small browser flow, then advance. Do not repeatedly benchmark or rerun entire suites without a reason.
7. **Do not rewrite the working retrieval platform to fit demo fixtures.** Fix an explicit API-to-view-model seam and incomplete workflow behavior. Keep immutable source records, hashes, private schemas, signed owner identity, origin checks and loopback bindings.
8. **This task produced documentation and a read-only UI preview only.** It did not integrate the newest UI or change the running application.

## Architecture Overview

```text
Latest modular Atlas UI, served same-origin
  -> one REST/SSE client + explicit wire-to-view adapters
  -> owned sessions and server-controlled runs/modes/revisions
  -> AgentRunner + bounded registered native provider tools
       -> shared RetrievalEngine.search (also used by direct search/admin)
       -> fetch original records -> evidence snapshots
       -> compare/pattern/visual context services within authorized scope
  -> deterministic claim gate -> transactional answer/state persistence
  -> answer_validated public event -> evidence-backed answer display

Visual surface: local allowlisted geometry + reviewed mapping/context
  + cited historical claim references + separately labelled user report
  + educational document references; never an automatic diagnosis
```

Python 3.11, FastAPI/Uvicorn, Pydantic 2, asyncpg, PostgreSQL 17/pgvector, rank_bm25, Sentence Transformers, vanilla HTML/CSS/ES modules and authored SVG. No new frontend framework, Redis, graph database, learned ranking stack or 3D engine is needed for this integration.

The actual provider harness uses the OpenAI-compatible SDK and explicit native tool-call/result pairing. PydanticAI was in the original design/dependencies, but this runtime is not a completed PydanticAI graph implementation. Stabilize the existing bounded harness before considering a framework replacement.

### Retrieval decisions already implemented

- Local `BAAI/bge-small-en-v1.5`, pinned revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`; 384 normalized dimensions, CPU, existing local files.
- Two representations per row: `problem` and `problem_action`. Facility has no ACTION and must continue to show null, not a fabricated action.
- Real raw BM25 + normalized BM25 + exact dense cosine; bounded top-50 channel recall, weighted RRF with weights 0.5/0.5/1.0 and k=60.
- Compatibility distinguishes component, symptom, number, side and negation; duplicate grouping preserves original IDs.
- Immutable-source annotations/duplicate sets cached; compatibility pair assessment moved to fused candidates; bounded query-embedding cache of 500 entries; one startup warmup.
- Optional `cross-encoder/ms-marco-MiniLM-L6-v2` is not loaded/enabled. Quality mode reports `reranker_unavailable`; do not label it active.
- Admin includes raw records/hashes, source evidence, stage timings, raw trace, feedback export, corpus browser, database capacity and deterministic PCA2 of all records. The 2D map is inspection only, not a relevance score or proof of clusters.
- Amazon-inspired work means staged cheap recall -> bounded pair comparison -> optional rerank, with evaluation. No trained Amazon replica/LightGBM matcher is present.

## Live-verified environment and progress

Rechecked during this handoff audit:

| Check | Observation |
| --- | --- |
| Health | `ready`, `app_ready`, `retrieval_ready`, `database_ready`, `workflows_ready` true; no startup errors |
| Provider | `provider_configured: false`; extractive answers remain available |
| Modes advertised | EVIDENCE, HYPOTHESIS, CHALLENGE, DISTINGUISH, SENSITIVITY, HANDOVER; advertisement is not proof all modes satisfy the plan |
| Supabase rows | 6,169 aviation + 200 facility = 6,369 |
| Vectors | 12,738 |
| Database footprint | 46,773,939 bytes at audit; configured quota 500,000,000 bytes; full corpus fits, no subset needed |
| Aviation corpus ID | `2795c1d6-a5f4-5c8d-a773-4ac724d10e99` |
| Facility corpus ID | `b5f9d886-1b2c-56cc-96fe-ae0488597043` |

Supabase project: `maintenance-copilot`, project ref `cjtokhnlwoqjeifmnwho`, kushaan's Org, Mumbai. Existing application schema `maintenance`, vector schema `extensions`; 24 app tables and migrations 001–006 were installed. App role is restricted; public/anon/authenticated app-table access was revoked. Preserve verified TLS and the pinned CA. Backend queries PostgreSQL directly through asyncpg; putting a Supabase service-role key in the frontend is unnecessary.

Runtime: Docker API `maintenance-atlas-p1-api-1` on loopback port 8000; project local DB `maintenance-atlas-p1-db-1` on 55432 retained for isolated tests. Old unrelated hybridsearch containers were stopped and volumes preserved. Temporary API previews on 8100/8101/8102 were stopped. Do not send the user back to 8102.

Earlier local disk observation: external project volume ~336 GiB free; internal drive only ~3.3 GiB free. Recheck before new downloads/build caches. Existing models ~139 MB; no new model download is needed for the normal retrieval flow.

Latest focused verification before this handoff: 12 lab/UI checks passed, Python lint and JS syntax passed, live UI source modal loaded real originals without console errors. Three representative search requests took 66–121 ms HTTP; a cached repeat took 37 ms; another browser request took 141 ms. These are spot checks, not a latency percentile/SLA. A prior frozen 15-question engineering set scored 12/15 Hit@5; labels are provisional, not organizer gold or evidence of perfect relevance.

The earlier null `.style` search alert came from inconsistent UI/script assets during redesign. The reviewed fix uses versioned lab assets, HTML no-store, matching DOM IDs, guarded UI updates and separate render/request error handling. Retain that fix when merging.

## Critical Files

Read these in this order. Paths without an absolute prefix are relative to the canonical checkout; latest UI-only paths must first be obtained from the pinned UI branch.

| Source / file | What it establishes |
| --- | --- |
| User-specified local IMPLEMENTATION_PLAN, sections 8–15, 17–20 and prompt appendix | Evidence gate, modes, tool authority, SSE/history, visual knowledge separation and acceptance requirements |
| [Original frontend handover, pinned](https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks/blob/caf2be389998ab9b062e9c591962197956a585c5/INTEGRATION_HANDOVER.md) | Latest UI decisions, demo limitations and contract mismatches |
| `docs/handoff/references/INTEGRATION_HANDOVER.frontend-caf2be3.md` | Byte-for-byte local copy of that upstream handover; read its local-scope caveat |
| `docs/handoff/references/latest-ui-wing-demo.png` | Actual browser observation of the newest branch's flap view; explicitly demo, not live evidence |
| `docs/backend/GITHUB_INTEGRATION.md` | Earlier b66fe7a resolutions; incomplete with respect to newer UI commits |
| `api/main.py` | Composition, lifecycle, capabilities, product/static routes and separate lab |
| `maintenance/contracts.py` | Canonical wire models, `extra='forbid'`, claim/support/session/action shapes |
| `api/routes/sessions.py`, `actions.py`, `runs.py`, `pins.py`, `observations.py`, `uploads.py`, `visuals.py` | Actual accepted payloads and current workflow gaps |
| `maintenance/agent_run.py`, `maintenance/agent.py`, `maintenance/models/provider.py`, `maintenance/tools.py` | Actual inference/tool dispatch, validation/release orchestration and prompt loading |
| `maintenance/answer_validation.py`, `answer_rendering.py` | Finite approved extractive templates, exact source spans, fallback and allowed actions |
| `maintenance/session_repository.py`, `events.py` | Persistence, JSONB fix, ownership/revision/run history and SSE replay |
| `maintenance/features/visuals.py`, `config/component_catalog.json`, `config/visual_mappings.json` | Existing component context and piston SVG mapping; not the new 33-region catalog |
| `docs/prompts/maintenance_system_prompt.md` | Full current runtime prompt; loaded by get_system_prompt() |
| `api/static/maintenance/maintenance-ui.mjs`, `api-client.mjs` on UI branch | Existing renderer/client that needs canonical adaptation |
| [airframe-mapping.mjs (latest UI branch)](https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks/blob/caf2be389998ab9b062e9c591962197956a585c5/api/static/maintenance/airframe-mapping.mjs), `component-explorer.mjs`, `wing-profiles.mjs`, `workspace-navigation.mjs` on UI branch | Latest region selection, cutaways, educational scenario and navigation |
| [atlas-workspace.css (latest UI branch)](https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks/blob/caf2be389998ab9b062e9c591962197956a585c5/api/static/maintenance/atlas-workspace.css) on UI branch | Latest overrides, compact layout, animation and reduced-motion behavior |
| [airframe-mapping.test.mjs (latest UI branch)](https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks/blob/caf2be389998ab9b062e9c591962197956a585c5/tests/ui/airframe-mapping.test.mjs) on UI branch | Region/wing mapping regression checks, not live integration proof |

## Immediate Next Steps

1. Fetch again and inspect status/branch drift. Create an integration branch from the latest P1 backend, incorporate the latest Person Two frontend with explicit merge resolutions, and retain both commit ancestries. Do not reset, force-push or overwrite either person's local changes. The newest UI baseline is Person Two, not main.
2. Fix same-origin product serving and the wire adapter. Get one real search -> exact source -> session message -> validated streamed answer/refusal -> reload flow working with the approved layout.
3. Fix release/state/cancellation and terminal/replay gaps before trusting multi-action UI behavior. Then connect reviewed component context and real claim supports into the existing compact visual explanation.
4. Finish the action-specific behaviors, model selection policy, uploads/pins/history restore and plan-required gaps below. Verify a small meaningful set after each substantial implementation slice; do not use repeated testing as a substitute for implementation.

## Safe integration and running instructions

Current branch is already published. At implementation start run `git status --short`, `git fetch origin`, and inspect both heads. Use a new local integration branch from P1 if isolation is needed. Merge the pinned/latest Person Two branch deliberately; preserve backend Settings, private-schema/TLS config, migrations, JSONB fixes, source validation, retrieval/lab and active tests. Do not accept incoming shared files wholesale just because the UI branch is newer.

The UI's relative the relative maintenance-ui.mjs module and CSS URLs require a directory base. Recommended: `/maintenance` redirects to `/maintenance/`; `/maintenance/` serves the new index, with absolute `/static/maintenance/...` asset URLs or a correctly mounted product directory. Ensure nested modules/assets resolve. Keep retrieval lab separate. Mount exactly one investigation controller; do not load legacy maintenance.js, talent.js or agent-panel.js beside the modular controller. Version assets on release; avoid exposing mutable worker files as the user's stable app.

Existing private profiles: `.env`, `.env.supabase`, `.env.gemini`, `.env.test` (ignored, restricted permissions). Do not overwrite them. The managed deployment intentionally has no active generation key. A saved key's presence is not consent to remove provider timeouts, loop over paid requests or claim generation works.

From the canonical checkout, the verified managed-backend invocation is:

```sh
docker compose --env-file .env --env-file .env.supabase -f compose.yaml -f compose.supabase.yaml config --quiet
docker compose --env-file .env --env-file .env.supabase -f compose.yaml -f compose.supabase.yaml build api
docker compose --env-file .env --env-file .env.supabase -f compose.yaml -f compose.supabase.yaml up -d --no-build api
```

Start only required services. Never print non-quiet Compose config. Keep host binding loopback. Do not perform migrations against Supabase unless new reviewed schema work requires them; never re-ingest/delete existing production records to make a UI test pass. Use the isolated test profile for DB tests, not `.env.supabase`.

Configuration names to understand: DATABASE_URL, DATABASE_SCHEMA, VECTOR_SCHEMA, DATABASE_SSL_ROOT_CERT, DATABASE_STATEMENT_CACHE_SIZE, APP_ORIGIN, PORT, SESSION_SIGNING_SECRET, LLM_PROVIDER, GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL. Verify exact aliases against `maintenance/config.py` and Compose before changing any. No key is needed for local BGE embeddings. Current model allowlist strings are configuration, not a statement about provider catalog availability; verify the chosen endpoint/model with one bounded live check before enabling its UI option.

## Contract adapter: current frontend versus actual backend

Implement a dedicated normalization boundary (suggested new module: maintenance-view-model.mjs) or update client and renderer consistently. Do not scatter fallback property guesses across the UI. Version/freeze representative JSON fixtures; if a canonical schema changes, update the Pydantic model, generated schemas, backend handlers, adapter and fixture together.

| Seam | Actual canonical behavior | Required UI integration |
| --- | --- | --- |
| Capabilities | configured_models, provider_configured, corpora, domains, reranker_available, enabled_modes, workflows_ready, agent_ready | Derive model/readiness labels, counts and mode availability. Extractive mode is usable even without a provider. Do not confuse agent_ready with live LLM verification. |
| Search POST | SearchSpec: query_raw, domain, top_k 1–10, intent, quality_mode, collapse_duplicates, optional corpus_ids/filters | Translate frontend query/quality/duplicate_policy fields; clamp UI limits to 10. Do not send demo fields or browser-derived mentions as authority. |
| Search result | SearchResult.hits + channels, versions, timings_ms, trace; each current hit includes record_snapshot | Build record view models from original_fields/raw data; retain corpus_id, compatibility, duplicate IDs and ranking. Use current snapshots for display but source/citation resolution still uses authoritative lookup. |
| Original record | GET records/{domain}/{source_id}?corpus_id=UUID | Derive domain/source_id from namespaced record_id; never rename corpus_id to corpus_version on the wire. Keep file provenance hash separate from per-field support hash. |
| Message POST | Exactly text, idempotency_key, expected_revision | Current UI sends message/model/search_spec and reads revision. Send text and current state_revision. Add a separately validated server contract for any desired model/search controls, or disable controls until implemented. |
| Message response | run_id, session_id, mode, state_revision, events_url | Use returned event URL; response revision is the input revision, not completed state. Refresh snapshot after release/done. |
| Session snapshot | state_revision; flat BoardItem[]; messages with role/content; answers[]; active_run_id | Normalize board grouping and message/answer timeline. Avoid duplicate answers from messages and answers; preserve source mode. Current snapshot has no pins or records array: add owned APIs/snapshot support rather than invent them. |
| Answer | AnswerEnvelope.claims with claim_type; status, limitations, missing, clarification, visual_refs:string[], allowed_actions | Group claims for display: problems/descriptions, historical actions, comparisons, receipt results. Existing renderer expects findings/action arrays and visual objects. All adapters retain original support objects. |
| Action authorization | AllowedAction.action lowercase + parent_answer_id + state_revision | Display human labels but post lowercase enum with the bound parent/current revision and fresh idempotency key. Hide unsupported actions; do not infer authority from a visible button. |
| Action response | Currently mixed: hypothesis returns envelope; distinguish/challenge/sensitivity immediate data; handover returns Markdown | Current UI assumes every action returns a streamable run. Either normalize all stateful actions to real persisted runs/events or explicitly handle synchronous results. Do not subscribe to undefined run_id or manufacture completion events. |
| Visual refs | Strings currently carry component refs; visual service supports one asset_id engine_concept_piston_2d | Resolve component context, then reviewed asset/hotspot mappings. A component ID is not necessarily an asset ID, and a piston schematic is not the transport-airframe cutaway. |
| Pins | PUT body user_note/expected_revision; implementation picks first matching corpus; DELETE ignores version/revision; snapshot omits pins | Fix exact corpus identity and atomic revision behavior plus owned list/restore; adapt requests. Do not silently pin a different source version. |
| Upload | Current route reads file only, despite client sending expected_revision | Bound streaming/read size before unbounded memory allocation, store owner/session/trust, freeze revision semantics and explicit attachment references. Extraction alone does not make it agent context or verified documentation. |
| Profile/observations | PATCH profile/title and POST observation routes exist | Use them explicitly; pasting an aircraft name into chat does not persist a verified profile. Preserve origin/status/revision. |

### Canonical event payload mapping at this checkpoint

| Event | Backend emits now | UI currently expects | Required behavior |
| --- | --- | --- | --- |
| query_interpreted | query_raw, domain, unsupported_request_detected | query, domain, applicability | Normalize query_raw; derive unknown applicability from trusted context, not a diagnosis. |
| search_completed | hit_count, record_ids | Mostly activity status | Attach/resolve immutable search ID and telemetry if needed; no invented source packet. |
| tool_started/completed | Prefetch get_records name/IDs/count, usually no tool_call_id/args/result | paired IDs, names, args/summary/result | Emit actual sanitized calls with real provider IDs and outcomes. Log provider-dispatched calls too; deps.tool_events alone is not public SSE. |
| evidence_ready | evidence_snapshots_count only | records[] | Add bounded authorized packets or a run-scoped evidence endpoint and fetch them. A count cannot be transformed into real records by the adapter. |
| board_updated | board_items_count + column counts | grouped board | After committed state, send typed BoardItem[]/revision or refetch snapshot. Counts are not board text. |
| answer_validated | envelope + answer_id/status/headline/claims_count/new_state_revision | answer | Normalize data.envelope; apply revision once. Never render provider drafts. |
| run_failed | error string | message | Sanitize server exceptions; use a stable safe error/status. No raw exception/provider text in UI. |
| run_cancelled/done | Terminal events | UI receive handles both, but subscribe stops only on done | Stop subscription/retries for all terminal events, release busy state and restore snapshot. |

## Streaming, persistence and workflow correctness still to implement

The plan's streaming means **live public activity first, released evidence-backed answer second**, not raw token streaming. Show a small progress line and expandable tool activity while work runs. Buffer all answer drafting. Reveal the answer only after the server commits a validated envelope. A visual can show user-mentioned orientation immediately, but that is a separate user-report layer.

Source-inspected gaps that the next implementation must address:

1. **Cancellation:** cancel route uses sequence 999999, which fails the strict contiguous client check. It updates DB status but does not cancel a tracked runner task; commit_answer_and_state can mark it completed later. Use per-run transactionally allocated sequence numbers, task cancellation/cooperative checks, and a terminal status guard in the answer commit. A cancelled run cannot publish a later answer.
2. **Replay terminal state:** EventBus.subscribe replays terminal events but then waits for live events; UI subscribe treats only done as terminal. Close correctly after replayed done/run_failed/run_cancelled; reconnect only to the same owned run from the last applied sequence, without another POST/model run.
3. **Release consistency:** board_updated currently occurs before final answer validation. If validation fails, new_board was already constructed from the rejected answer; fallback is not fully revalidated. Build board from the final released answer, revalidate the fallback, commit answer/board/revision atomically, then publish events. Never retain rejected findings in the board.
4. **Commit-to-event crash window:** answer/state transaction and final public events are separate. Add a durable outbox or recover terminal events from committed state so a crash after commit cannot strand the UI forever or cause another inference. Add startup reconciliation/leases for abandoned queued/running tasks; asyncio.create_task alone is not restart durability.
5. **History actually used by model:** model transcripts are stored, but execute_run constructs a fresh system/user pair from this question plus prefetch evidence; it does not restore prior turns/board/profile into the provider context. Load bounded trusted session state and complete native tool pairs; keep hypotheses/uploads untrusted. Browser history restoration alone does not satisfy conversational reasoning continuity.
6. **Context authority:** inject RUN_MODE/RUN_ID/SESSION_ID/STATE_REVISION/corpus versions/profile/board/budgets as server context. They are not all currently injected even though the prompt describes them. Enforce mode/tool scope outside the prompt.
7. **Budgets and errors:** provider loop is bounded to 3 turns, 8 tool calls, 25 seconds in current runner. Deterministic prefetch and subsequent tool calls need a coherent total budget/deadline, registered argument validation and safe error categories. Never broaden source scope or silently replace a failed search with hypothesis generation.
8. **Nonclaim output validation:** exact span/finite-template claim checking is implemented. General semantic entailment checking, safe resolution of gap/limitation references, allowlisting visual refs and complete envelope-level checks are not established by this code. Current runner copies model limitation_refs/gap_refs/clarification_ref into user text. Resolve trusted IDs to server templates or validate them; no hypothesis/advice loophole in headline, question, limitation or visual caption.
9. **Source-context truthfulness:** VisualService returns source_available=true even for missing/unknown catalog context. Curated prose/citations are authored strings, not verified manual excerpt/hash packets; some prose overstates causality/outcomes. Review/narrow and provide real document provenance before calling explanations source-backed. Unknown component -> unavailable state, not invented reviewed content.
10. **Other writes:** observation checks revision outside its UPDATE; pins do not enforce a locked revision; uploads do not implement the advertised revision semantics. Harden atomicity and ownership consistently before concurrent UI actions rely on it. Preserve the existing native JSONB codec fix; do not reintroduce nested JSON strings.

Keep timings distinguishable: client HTTP, server search total, queue, embedding/cache hit, channel recall, compatibility, fusion/dedup, optional rerank, provider duration, validation, evidence fetch, total run. Do not present overlapping stage spans as a sum or prefetch counts as real tool-call details. Product UI should show a compact duration/degraded indicator; detailed diagnostics belong in the disclosure or retrieval lab.

## Display and interaction specification: keep the newest UI flow

### Normal investigation

1. Sidebar and one issue/follow-up composer remain the starting point. Teal sidebar, light neutral canvas, green primary action and coral mentioned-region highlights remain. No second hero composer and no restored removed sample-card sections.
2. Typing may highlight named exterior regions with **“Mentioned in your issue”**. It cannot assert that a source confirms the fault. Unknown text selects nothing; ambiguous side can highlight both with an ambiguity note. Cylinder #2 must never select engine 2. Negated or multiple issues need explicit handling rather than first-keyword diagnosis.
3. Submit creates one owned server run. Keep the user's wording visible, show actual activity and allow Stop. Do not switch to demo or display eight invented DEMO records on an API error.
4. On validated release, lead with a narrow readable historical summary/status, then grouped cited findings and recorded actions. Follow with material differences, missing information and one useful clarification if supported. Do not dump JSON or expose hashes in the main narrative; source drawers and diagnostics carry details.
5. Desktop: conversation/answer primary; adjacent evidence/board/visual tabs share the active investigation. On small screens stack them with citation access close to each claim, no competing full-width explanations. Keep the user's approved large aircraft and compact selected-part panel together.
6. Source-backed historical output uses wording such as “Record aviation:103578 records replacement of an intake gasket.” Never convert it into “Replace the gasket”, “the repair worked”, “safe to fly”, or “applies to this engine”. A valid hash proves text identity, not repair efficacy or claim entailment.
7. Preserve full source fields in the drawer. Citation click selects exact raw field/span, highlights Unicode code-point offsets, shows namespaced record ID, corpus UUID, field hash, recorded file provenance hash and applicability. Missing/mismatched hash must not receive a Verified badge. Do not cite normalized or reconstructed text as an original log.
8. Side board uses origins: Known=user report/configuration with source; Reported=validated historical claims; Missing=unresolved information/applicability. Hypotheses never populate Reported or become known facts. New observations supersede prior entries; old answers retain their revision.
9. Show contextual actions only when the server actually supports them and the parent/revision is eligible. Keep advanced search off the normal path; the separate retrieval admin remains available as a testing/inspection tool.
10. Live chrome must say live historical corpus/locally hosted backend, with unknown aircraft linkage. Remove demo workspace badges, Vansh-specific user identity and logo links forcing `?demo=1` in live mode. Demo remains an explicit separate choice, with its own storage/pointer namespace.

### Seamless visual + explanation + evidence behavior

Use a single selection state shared by evidence cards, exterior airframe and internal part explanation. Do not mount a second interactive SVG with duplicate DOM IDs in the Airframe Visual tab; move/reuse the explorer or namespace cloned IDs and synchronize state deliberately.

- **Exterior selection ->** open the matching internal profile, preserve the query and selected answer. Keep Back to full airframe. No automatic new search on every hotspot click; offer a removable visible “Search this component” chip.
- **Internal selection ->** update the selected callout, small part list and one compact explanation box in place. Preserve the six specific wing profiles: slats, flaps, ailerons, spoilers, tank/wing box and winglet. Do not map them all back to a generic four-part diagram.
- **Historical claim/citation selection ->** focus only a reviewed exact/approximate component mapping, then show the matching raw supports in the same compact context area. If no mapping exists, retain the citation and say the internal location is unknown; do not force a picture highlight.
- **Answer ->** may return only allowlisted stable component references. Resolve through the component-context service; never let model output choose executable markup, CSS selectors, SVG coordinates, arbitrary asset URLs or HTML.
- **New query/answer ->** update the active evidence layer but do not erase an explicit user's manual part selection unexpectedly. Offer “Focus related component” when useful. Label context by answer/run/revision so old results cannot appear to describe a newer observation.

Keep three clearly labelled blocks within the existing compact panel, not three giant panels:

| Block | Content / authority | Empty behavior |
| --- | --- | --- |
| **Reported issue** | User wording and selected region; “user reported / location unconfirmed” | Neutral orientation, no fault diagnosis |
| **What matching logs record** | Atomic released claims, record/field citations and exact supporting quotes scoped to this part | “No cited historical evidence identifies this internal part.” |
| **About this component** | Reviewed educational explanation, document locator/hash/revision, generic/unknown applicability | “Reviewed educational context unavailable.” |

Separate **“What could follow? — educational, unverified”** and **“Possible solutions — unverified”** from the evidence answer. Neither auto-expands when results arrive. Existing static `issueScenario()` text is educational scenario logic, not model reasoning or log evidence; label it accordingly and verify its documentary basis before displaying stronger consequences. No predicted timeline, inevitable progression, damage severity, fictitious sensor telemetry, repair sequence or fabricated crack/bearing/seal condition.

### Required reviewed visual-binding contract (new implementation work)

Current UI uses exterior SVG IDs and numeric internal callout indices; backend catalog uses conceptual piston component IDs. They are not a single registry. Introduce a versioned reviewed mapping rather than string-matching arbitrary words into all three layers.

For each binding retain: mapping revision, approved asset/profile ID, exterior region ID, stable internal_part_id (not array index), canonical component_id, exact/approximate relation, mapping basis (user mention / historical span / reviewed education), ambiguity, applicability and optional released claim/support IDs. Store evidence references with run/answer/revision/corpus IDs. Derive source bounds from validated support objects, not client text. Do not map a piston intake-gasket claim to a transport turbofan seal solely because both are engines.

A proposed response shape to freeze with a Pydantic model (not a currently implemented route):

```json
{
  "mapping_revision": "reviewed-version",
  "component_id": "intake_gasket",
  "asset_id": "engine_concept_piston_2d",
  "exterior_region_id": null,
  "internal_part_id": "intake_gasket",
  "mapping_relation": "approximate",
  "mapping_basis": "historical_span",
  "applicability": "unknown",
  "illustrative": true,
  "claim_refs": [],
  "knowledge_refs": [],
  "unknowns": ["Aircraft model and engine-side applicability are not established"]
}
```

This example deliberately has no transport-engine exterior mapping and no fabricated evidence IDs. Freeze actual enum names/route with the implementation; do not pass this proposed object to an existing strict schema unchanged. Historical source refs and educational document refs remain distinct unions. Review all 33 regions incrementally; unsupported contexts can ship as labelled orientation-only views. A user-selected aircraft model never changes a log's source_model or applicability.

## Model behavior, tools and prompt integration

Read the full existing runtime prompt at `docs/prompts/maintenance_system_prompt.md` and plan appendix. Keep it versioned, load it server-side and inject typed authoritative context. Do not just paste more instructions into user messages and call the behavior enforced.

### Existing registered tools and gaps

| Registered now | Actual role | Integration responsibility |
| --- | --- | --- |
| search_records | Shared hybrid retrieval; query/domain/top_k | Carry source scope, search identity, real ranking/timing and declared filters into the UI; expose tool calls only when they occurred |
| get_records | Bounded original fetch and evidence snapshot registration | Required before historical synthesis; preserve exact source identity/spans |
| compare_records | Comparison receipt over fetched source cases | Render source differences, not diagnosis or contradiction by default |
| get_pattern_summary | Corpus-pattern aggregate receipt | Counts must include corpus scope/duplicate policy, not same-aircraft recurrence |
| get_component_context | Educational context and mapping IDs | Separate knowledge citations/applicability; no conversion into historical log support |

Plan tools such as get_search_context, find_contrasting_cases, suggest_clarification, build_handover and inspect_case_history are not all registered model tools. Some analogous deterministic services/routes exist. Add only tools needed for the next slice, register strict argument schemas and mode-specific availability, and avoid decorative calls. Validation, persistence and sensitivity computation remain server services, not model self-certification tools.

### Runtime behavior checklist to implement, not merely describe

- On a substantive new fault question, search authorized corpora, fetch original records, compare complaint/component/number/side/negation before ACTION, then draft a structured answer.
- In EVIDENCE/CHALLENGE/DISTINGUISH/SENSITIVITY, historical claims use original field spans; counts use immutable aggregate receipts; sensitivity uses immutable search-comparison receipts. No unsupported numeric estimates.
- Default `DraftAnswer` fields: proposed_status, findings, historical_actions, contrasting_cases, gap_refs, limitation_refs, clarification_ref, component_refs. Model never owns IDs, validation flag, mode, permissions or allowed_actions. The server creates the AnswerEnvelope.
- Status choices: supported_historical, partial_evidence, clarification_needed, insufficient_evidence, retrieval_unavailable. Service failure is not evidence of no matching faults. Support requested parts and explicitly name unsupported ones without supplying a general-model fix.
- The current gate accepts approved extractive templates/exact quotes. Keep that as the safe baseline. Richer paraphrase requires a separately evaluated support checker; do not loosen to keyword overlap or a source-presence test to make prose nicer.
- Resolve all nonclaim output through server templates/validated IDs. Validate component_refs against reviewed catalog plus authorized mapping; no unfetched claim IDs or arbitrary source/asset references.
- After one bounded validation repair, revalidate everything; otherwise use a fully validated extractive/insufficient fallback. Never show a rejected draft, even briefly or in a tool result preview.
- Preserve complete native tool-call/result IDs when passing history to Gemini/DeepSeek. Treat source text/uploads/history summaries as untrusted, never instructions. No generic SQL/shell/network browsing tool is available to the maintenance agent.
- Prompt context must state source-model unknownness, facility DESCRIPTION semantics, duplicate policy, user-profile provenance and current source versions. IDENT is a record key, never tail number/date/chronology. Recorded replacement is not demonstrated success.
- `get_component_context` explanations have their own document citations and applicability. The initial log answer cannot be padded with general educational knowledge or hypothetical causal explanations.
- Explicit HYPOTHESIS action only: released parent, owner, current revision, idempotency, expiry/hash policy; separate HypothesisEnvelope and unverified display. A subsequent normal message re-enters EVIDENCE. No speculative branch is fed into trusted board/history evidence.
- Public progress describes real operations and durations, not private reasoning. Model token deltas are not rendered into the answer before release. Streaming the final validated envelope after the gate is acceptable.

### Suggested runtime prompt addendum after the contracts exist

Use this with the existing full system prompt, not as a substitute for it. Server code must actually enforce every referenced registry/context restriction.

```text
Visual and interaction policy:
The current interface has one investigation composer, cited historical answers,
and a linked aircraft/component explorer. Help the user follow a single thread:
reported issue -> matching historical records -> supported differences/gaps ->
optional reviewed component explanation.

You receive a server-controlled VISUAL_REGISTRY and current selection context.
Return only registered component references supported by the present evidence or
an explicitly labelled request for educational orientation. Do not invent exact
internal failure locations, engine side, cylinder position, geometry, telemetry,
SVG coordinates, selectors, URLs, HTML or code. If no mapping is supported, return
no highlight and identify the unresolved location through an approved gap ID.
The user's selected airframe and a generic drawing do not establish historical
record applicability.

Keep historical claims in the evidence envelope with fetched original spans.
Component education is a separately cited knowledge surface, never a replacement
citation for a log claim. General possible causes and conditional complications
must not appear in the initial historical answer or leak into its headline,
limitations, question or visual caption. Hypotheses require the authorized
separate mode and remain visibly unverified thereafter.

Draft a structured envelope; do not emit free-text answer tokens to the UI.
Only server-validated output is released. Public progress may name actual tool
operations, source counts, elapsed time and service degradation. Never expose
private reasoning or describe a tool as executed before its real result exists.

Use concise plain language. State what a record reports, then the material gap.
A citation should let the user inspect the exact text and return to the same
selected component without losing the investigation. Do not present a ranking
score, hash check, animation or repeated wording as diagnostic certainty.
```

## Remaining action modes and plan coverage

| Work | Current reality | Completion target |
| --- | --- | --- |
| Challenge | Alternative-search service exists; route returns immediate result | Persist evidence-only child run, preserve parent complaint and source scope, fetch/compare alternatives, release supported revision or truthful no-contrast statement |
| Distinguish | Comparison service/receipt exists; route returns data | Two to six authorized fetched IDs, supported dimension table; durable receipt and sources; no improvised inspection steps |
| Sensitivity | Route constructs base from answer headline and hardcodes intake/rocker queries | Use immutable original SearchSpec and explicit user-approved single-variable variant; preserve other filters/model/corpus; max three changes; computed top-five overlap/rank deltas; no causal interpretation |
| Hypothesis | Separate conceptual service/envelope exists; synchronous commit, not full streamed agent exploration | Enforce current parent/hash/revision/idempotency; do not recommit duplicate run; label unverified; separate history and no board contamination; truthful provider/source basis |
| Handover export | Markdown generated; hypotheses excluded by default | Add full immutable source/corpus/field hash/receipt/mapping versions and source origins; no maintenance signoff; optional separately labelled speculative appendix |
| Recurrence | Pattern service available | Expose scoped raw row/distinct-pair receipts with duplicates; no same-aircraft recurrence, MTBF or repair success |
| History | DB snapshots/model transcripts exist | Restore actual timeline/board/profile/pins/citations and active stream; model consumes bounded trusted history; recover abandoned tasks after restart |
| Saved evidence | Pin routes incomplete | Corpus-version-preserving owned CRUD/list, revision checks and restore; pin means saved, not approved repair |
| Upload/report | Extraction/storage route exists | Bounded bytes/MIME/extraction; explicit attachment refs in run context; untrusted source labels; PDF extraction failures visible; no automatic corpus promotion |
| Model/quality controls | UI selector + allowlist, but message contract cannot select model; reranker disabled | Server-validated supported selection or clearly disabled control; record actual effective model/fallback; no fake active reranker/provider |
| Aircraft/profile | Session profile/observation routes exist | Optional user-reported configuration, correct revision/origin; no source applicability upgrade |
| Public deployment/submission | User currently requests local only | Defer public exposure; record unresolved deployment/organizer data-rights/demo/pitch requirements separately |
| Evaluation | Engineering spot checks and provisional 15-query set | Human relevance/claim review, duplicate-aware heldout split, semantic support evaluation before free paraphrase; broader p50/p95 only once final implementation is stable |

## Ordered implementation slices and acceptance

**Slice 1 — integrate newest UI + real retrieval.** Merge frontend branch, resolve serving/assets, implement capabilities/search/record adapters and live/demo chrome. Prove a real aviation query and facility description display original source/corpus/hash; top K respects 1–10. Preserve retrieval admin working. No LLM key required.

**Slice 2 — one reliable investigation.** Normalize message/session/answer/event shapes, render only released claims, fetch evidence packets, fix snapshot restoration, terminal SSE, cancellation and committed revision handling. Prove submit -> sources -> answer/refusal -> refresh/reconnect with no duplicate run/answer. Keep public progress compact; raw traces expandable.

**Slice 3 — linked visual evidence.** Freeze reviewed stable part mappings and component-context schema; share selection across explorer/evidence. Prove one source-supported piston component maps only to its valid conceptual asset; unknown transport-airframe mapping remains unknown. Check six wing profiles still distinct, keyboard selection, clear source labels and compact panel. No invented log-to-part relationship.

**Slice 4 — model context and advanced actions.** Add bounded session/tool history, authoritative prompt context, safe nonclaim fields, real provider verification, action-specific persistence/authorization and receipts. Fix sensitivity/hypothesis idempotency before enabling those buttons. Preserve extractive operation if external generation is unavailable.

**Slice 5 — reliability and finishing.** Upload/pin/profile atomicity, recovery/outbox, handover provenance, narrow/mobile/reduced-motion behavior, final targeted regression/security checks and documented remaining gaps. Rebuild local API and open the actual non-demo product URL. Commit meaningful slices to the designated repository; no force push or remote main merge without explicit authorization.

### Small acceptance matrix (after implementation, not a broad repeated test campaign)

- Real `CYL #2 intake leak`: matching originals and cited action, no engine-2 side claim; citation opens raw PROBLEM/ACTION with correct hash and offsets.
- `water leak` in facility: DESCRIPTION source, ACTION stays null, no invented repair.
- Unsupported torque/procedure question: supported historical parts only or explicit missing-source refusal; no uncited repair value.
- Unknown/ambiguous/negated complaint: no forced internal diagnosis or default right engine; unknown mapping visible.
- One browser run with SSE interruption/replay and one cancellation: no duplicate inference/answer, no event gap, no completion after cancel.
- Reload investigation: same answer IDs/support versions, board/profile/pins and selected context recover; no localStorage authority over server records.
- Hypothesis explicit click: separate unverified branch; normal next message evidence-only. Duplicate action key does not create/recommit a second result.
- One reviewed component explanation: knowledge citation separate from historical spans, unknown applicability visible; no fabricated telemetry/geometry.
- Cross-owner/origin/revision checks, Unicode source highlight and untrusted text remain protected. Use small focused contract/service tests, then one live browser walkthrough; run the wider suite once for the final integrated build if warranted.

## Decisions Made

- Keep the newest UI layout while preserving the canonical backend's strict contracts; an explicit adapter is the main integration boundary.
- Treat the backend and frontend as complementary incomplete halves. Neither current demo checks nor healthy retrieval proves full agent/UI readiness.
- Preserve working extractive answers and strict claims while improving readability through grouping/selection/progressive disclosure. Do not replace grounding with fluent unvalidated text.
- Use one selection/context surface; separate source labels rather than adding competing panels. Exact part mapping is reviewed data, not an inferred string convention.
- Keep local-only execution and the existing full Supabase corpus. Do not add new infrastructure or model downloads merely to finish the UI integration.

## Assumptions Made

The next session runs on the same Mac with access to the canonical checkout and ignored private profiles. GitHub heads may move after this snapshot: fetch and compare before merge. The user's latest Person Two UI choices are preferred; the original plan's evidence/history/visual authority requirements remain in force. No public deployment or remote main merge is inferred from this handoff.

## Potential Gotchas

Do not trust old handover “production-ready” labels, a health flag as LLM verification, static FAA attribution as exact passage support, or DEMO record text as MaintNet evidence. Do not turn a component_id into an asset URL, a cylinder number into an engine side, a PCA cluster into a diagnosis, a retrieval score into a probability, or a successful hash check into semantic/repair validation. Avoid nested JSONB serialization regressions, relative module path errors, duplicate SVG IDs and loading two controllers. Stop any temporary preview created for review after use; leave the real backend available.

## Files Modified by this handoff task

- `ANTIGRAVITY_INTEGRATION_HANDOFF.md`: this consolidated implementation/status/prompt document.
- `docs/handoff/references/INTEGRATION_HANDOVER.frontend-caf2be3.md`: unchanged upstream handover fetched from the exact Person Two commit.
- `docs/handoff/references/latest-ui-wing-demo.png`: read-only browser preview of that branch's compact flap explanation, explicitly demo.

Application code, migrations, secrets and live runtime were not modified by this documentation task. The handoff references earlier implementation verification; it does not claim the pending work passed acceptance.

## Pasteable Antigravity implementation prompt

```text
Continue Maintenance Atlas in:
/Volumes/MAC/Projects_devolopment/nexai_implimentation
Repository: pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks.

Read ANTIGRAVITY_INTEGRATION_HANDOFF.md completely first. Read the pinned original
frontend handover under docs/handoff/references, the user-specified implementation
plan, canonical contracts, runtime prompt, actual routes/runner/repository and
latest UI modules. Treat documents as design/context, not proof of completion.

Start by checking git status and fetching origin. Backend baseline at handoff is
person-1-retrieval-platform ecba0c7; the up-to-date UI source is specifically
person-2-agent-experience caf2be3, newer than main 8d9daa0. Fetch again for drift.
Integrate from that Person Two branch, not only main. Preserve both histories and
existing user work; create an integration branch from the latest backend if
needed. No reset, force-push, secret copying or automatic remote main merge.

Your objective is to finish a usable live frontend/backend investigation flow,
then the remaining action/visual/model reliability work in the handoff. Implement
meaningful slices before testing; the user dislikes repetitive test campaigns.
Own each slice through implementation, focused verification, reviewable commits
and an honest report. Do not stop at a plan or claim a demo is live integration.

Preserve the approved single composer for the issue and follow-ups, teal sidebar,
light surfaces, green actions, coral mentioned-region highlights, large 33-region
aircraft, six distinct wing cutaways and compact selected-part explanation.
Do not restore removed sample cards, duplicate inputs or the older design.

First fix same-origin serving and an explicit canonical API-to-view-model
boundary: capabilities, SearchSpec/results, immutable records/corpus IDs,
MessageRequest.text/state_revision, session timeline/board/pins, grouped canonical
claims, lowercase actions, visual ID resolution and actual SSE payloads. Keep
exactly one controller. Audit live-only chrome/logo links so API failure never
silently becomes demo. Keep /retrieval-lab independent and functioning.

Then make one real run reliable: owned session -> shared hybrid search tool ->
get original records -> exact evidence snapshots -> structured draft -> gate ->
transactional answer/board/revision -> answer_validated -> done -> restore.
Fix contiguous event allocation, all terminal/replay cases, task cancellation,
late-completion guards and commit-to-event recovery. Actual history/board/profile
and complete tool pairs must be passed to the model under bounded budgets.
Do not merely show browser history while the provider forgets prior context.

Use the existing runtime prompt plus the handoff behavior requirements. Inject
server authority for mode/IDs/revision/source versions/profile/board/budgets.
Historical claims require fetched source spans; exact record/corpus/field/hash
and Unicode offsets must match. ACTION means recorded action, not success or
recommendation. Facility DESCRIPTION never becomes ACTION. Keep the strict
extractive baseline; richer paraphrase needs evaluated support checking.
Resolve gap/limitation/clarification and visual refs safely. Revalidate fallback
and build the board only from the final released answer. Never display drafts,
private reasoning or invented tool activity.

Integrate visuals into the existing flow through one shared selection state.
User-mentioned region, historical support and educational knowledge are separate
labelled layers. Create a reviewed versioned mapping of canonical component IDs,
exterior IDs and stable internal-part IDs; current numeric callouts are not those
IDs. Citation selection should focus only a supported exact/approximate mapping
and show the same claim's raw evidence. Component click updates its small panel
in place; offer a removable query chip rather than silently launching searches.
No known mapping means explain the unknown, never invent a failed part. A piston
intake-gasket log must not become a transport-turbofan seal diagnosis. Keep
knowledge citations/applicability separate, review curated source claims, handle
source-unavailable truthfully, and never accept model HTML/SVG/coordinates/URLs.

Finish action-specific behavior deliberately: some routes currently return
synchronous results while the UI assumes streams. Normalize that seam; use
immutable original SearchSpec for disclosed single-variable sensitivity, durable
comparison/count receipts, and explicit current-parent/idempotent HYPOTHESIS
with a separate unverified envelope. Hypotheses never contaminate historical
answers or Reported board. Review upload/pin/profile revisions, corpus identity,
source restoration and full-provenance handover export. Do not enable buttons
until their semantics work.

Backend is already local on8000 and connected to Supabase; all6369 records and
12738 vectors fit. Local pinned BGE384d needs no API key. Provider is presently
unconfigured/extractive despite an allowlist and a privately saved Gemini key;
live generation was not verified. Keep secrets in existing ignored profiles,
verified TLS/private schema and loopback exposure. Do not expose a DB/service key
to the browser. Use a bounded real provider check before claiming model success;
otherwise preserve extractive operation with an accurate label. Reranker is off.

After each real implementation slice, run targeted tests/lint and a small relevant
browser flow. Before final completion verify real non-demo query/source/answer,
one refusal, facility null ACTION, replay/cancel/reload, reviewed visual linkage,
owner/origin/revision protection, keyboard/mobile/reduced-motion behavior and
no untrusted HTML. Do not claim perfect relevance or broad latency guarantees
from a few queries. Record exact changed files, commit SHAs, commands/results,
known limitations and the correct live URL. Keep all code/commits in the designated
repository. Do not publicly deploy or merge remote main unless authorized.
```
