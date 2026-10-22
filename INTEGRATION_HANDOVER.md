# Maintenance Atlas — current project context and integration handover

**Updated:** 22 October 2026, India time. **Audience:** Kushaan's backend agent and Vansh's frontend agent.

This is the current integration entry point. Older README/onboarding documents describe earlier stages. This handover records the inspected local checkout and the user's latest decisions; it does not assert the state of Kushaan's separate working copy or unfinished Supabase work.

## 1. Project and ownership

- NexAI 2026, problem statement 1.3: Maintenance Copilot — agentic RAG over aviation maintenance logbooks.
- Product: **Maintenance Atlas**, branded **atlas** in the current interface.
- Repository: https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks.git
- Laptop checkout: `C:\Users\Vansh\Desktop\NexaI`. All frontend work and preview screenshots are saved here.
- Frontend branch: `person-2-agent-experience`; backend branch in earlier briefs: `person-1-retrieval-platform`.
- Kushaan / Person 1: data ingestion, Supabase/PostgreSQL, retrieval, shared contracts/config/migrations/dependencies, API composition.
- Vansh / Person 2: UI, visual explorer, agent/evidence-release boundary, investigation workflows and history.
- User reports Kushaan is currently connecting the supplied 6,000+ log records to Supabase. Coordinate against his latest branch before merging; no remote backend audit was performed for this document.

The earlier data audit reports 6,169 aviation rows, 5,122 distinct problem/action pairs; optional facility corpus has 200 rows. These are documented corpus counts, not live Supabase counts verified in this frontend session.

## 2. Product rules and latest user decisions

- Make issue entry easy for a nontechnical user. Keep one textarea for the initial issue and follow-ups; results appear in that same investigation panel.
- The user removed the duplicate hero input, the "Not sure where to start" sample cards, and redundant marketing/step sections. Do not reintroduce those.
- Keep the current teal sidebar, light neutral surfaces, green actions, and coral/red issue highlights. The user likes the current plane and red highlights.
- Sidebar groups investigations, aircraft explorer, record search, history, saved evidence, uploads, feature directory, help, settings.
- Keep the aircraft large and visually appealing. Named wing regions must open their own internal diagrams and parts, not a shared generic four-item wing view.
- Keep diagram, internal controls and compact explanation together; avoid large repeated full-width text panels.
- User wants richer agent answers eventually but explicitly deferred changing answer presentation until backend/database/retrieval work is ready. The recent work did not redesign the answer format.
- User wants the red explanation box to become more informative with real evidence. **That requires deliberate integration; connecting the DB alone does not populate it.**

Core evidence semantics remain: logs establish recorded PROBLEM/ACTION text, not a diagnosis, repair success, aircraft model, chronology or model applicability. Future complications are conditional educational possibilities, not inevitable outcomes or timed forecasts. Do not invent telemetry, crack stations, seal failures or validated diagnoses to fill UI space.

## 3. What is actually working in the frontend

The explicit demo uses `?demo=1`, 18 invented `DEMO-*` records, and browser localStorage. It does not query Supabase, run an embedding model/LLM, or demonstrate a production evidence gate.

Working demo interactions include issue submission, related demo records, original-record/citation dialogs, pins, browser demo history, board display, simulated public activity, contextual action buttons, text/Markdown upload, and handover export. Some action modes are intentionally explanatory placeholders, not functioning comparison/hypothesis engines. Demo PDF extraction is unavailable. Browser history is not server-authoritative persistence.

Aircraft explorer:

- 33 selectable SVG regions; shaded fuselage, cockpit glass, windows, wing-control panels, winglets, engines/pylons, doors, landing-gear regions, tail/elevators.
- Larger desktop canvas, responsive scaling, keyboard selection, subtle fault-glow pulse, rotating fan in engine cutaway, reduced-motion CSS overrides.
- UI mention mapping for side aliases (left/right, LH/RH, L/H/R/H, port/starboard), engine numbering and named controls. Unspecified wing side highlights both. Cylinder numbers do not select an engine side.
- This is bounded keyword mapping, not a diagnosis engine, calibrated classifier or verified aircraft component catalog. Complex negation, multiple faults and ambiguous natural language need further work.
- Six separate wing profiles: slats (surface/support track/nose interface), flaps (panel/linkage/track-carriage), ailerons (panel/hinges/control connection), spoilers (raised panel/actuator/hinge), tank region (enclosure/spars-ribs/access/feed-vent), winglet (shell/root/reinforcement).
- Ten additional regional profiles now cover nose/radome, cockpit glazing, avionics bay, forward cabin, aft cabin, center box, tail cone/APU, horizontal stabilizer, elevator and rudder. Each has distinct geometry, three internal callouts and component-specific issue context. Landing gear, doors and pylons still use the generic structural view; not all 33 regions have unique internals. Engine retains its lubrication cutaway.
- Red internal areas identify illustrative candidates. The compact box follows the selected internal part and says its condition is unverified. Educational references are distinct from log citations.

## 4. File map

| File | Role |
| --- | --- |
| `api/static/maintenance/index.html` | Current page and 33-region aircraft SVG; one `chatForm` / `chatInput` |
| `api/static/maintenance/maintenance-ui.mjs` | Main API/demo controller, session/render logic, evidence/board/activity and explorer wiring |
| `api/static/maintenance/api-client.mjs` | Proposed REST adapter and incremental SSE decoder/replay checks |
| `api/static/maintenance/demo-adapter.mjs` | Explicit invented demo fixtures and browser persistence |
| `api/static/maintenance/airframe-mapping.mjs` | Query-to-exterior-region mention mapping |
| `api/static/maintenance/component-explorer.mjs` | Internal renderer and conditional educational scenarios |
| `api/static/maintenance/wing-profiles.mjs` | Six distinct wing diagrams, catalogs and profile-specific scenario context |
| `api/static/maintenance/airframe-profiles.mjs` | Ten additional regional cutaways, internal parts, issue rules and examples |
| `api/static/maintenance/demo-component-cases.mjs` | Ten invented regional records, selected through the same region mapping |
| `api/static/maintenance/workspace-navigation.mjs` | Sidebar navigation and feature directory |
| `api/static/maintenance/atlas-workspace.css` | Latest layout/design/animation overrides; loaded last |
| `api/static/maintenance/maintenance.css`, `talent-base.css` | Retained base styles; do not casually remove them before consolidating dependencies |
| `tests/ui/airframe-mapping.test.mjs`, `tests/ui/airframe-profiles.test.mjs` | Node regression checks for mapping, real SVG IDs, regional geometry and demo matches |
| `maintenance/contracts.py`, `contracts/v1/` | Existing canonical Python contracts/schema artifacts; not identical to the current demo view model |
| `api/main.py`, `api/routes/search.py`, `api/routes/records.py` | Existing backend composition/search/source endpoints |
| `docs/p1/PERSON_2_HANDOFF.md` | P1 service/lifecycle/auth interface handoff |
| `docs/work-split/` | Ownership and complete acceptance requirements |
| `docs/prompts/maintenance_system_prompt.md` | Evidence/mode/applicability prompt rules |
| `docs/p2/`, `docs/p2/previews/` | Per-change notes and actual UI screenshots |

## 5. Run the frontend preview

From the laptop checkout:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory api/static/maintenance
```

Open http://localhost:8765/?demo=1 . That port serves the static preview only. Omitting `demo=1` selects the live adapter; there is no silent fallback to invented evidence.

Examples to type manually (sample cards were intentionally removed): `Engine 1 oil leak`, `left wing flap stuck`, `RH aileron jammed`, `wings fuel leak`, `cockpit display blank`, `Radome crack near the attachment ring`, `Forward cabin window seal leak`, `Aft cabin pressure leak`, `APU exhaust vibration in tail cone`, `Left horizontal stabilizer crack`, `Right elevator stiff movement`, `Rudder hinge excessive play`.

Current demo DB key: `maintenance-atlas-explicit-demo-v2`. Session pointer key: `maintenance-atlas-demo-session-pointer`. Preserve or explicitly reset only this app's demo storage when testing; never clear unrelated browser data.

Backend launch documented by P1: `uv run python -m uvicorn api.main:app --host 127.0.0.1 --port 8000`. Database, pinned artifacts, provider configuration and exact origin must also be ready. Do not copy credentials into this document or browser code.

## 6. Critical integration gaps found in this checkout

**Do not assume the demo wire format matches the Python contracts.** Freeze the canonical contract with P1, then adapt the frontend at a clear boundary. Prefer an explicit normalization adapter or update the renderer/client together; do not weaken the backend evidence/auth rules to fit fixtures.

| Area | Frontend currently consumes/sends | Existing local backend/contracts | Required integration |
| --- | --- | --- | --- |
| Product route | UI lives in `api/static/maintenance/index.html`; relative asset URLs | `/maintenance` checks `api/static/maintenance.html`, which is an older path | P1 updates serving/redirect strategy. Serve a trailing-slash directory URL or correct asset paths. `/static/maintenance/index.html` is mounted through static serving already. |
| Capabilities | `models: [{id,label}]`, `domains`, `corpus_summary`, `rerank_available` | `configured_models`, `corpora`, `reranker_available`, `enabled_modes`, `workflows_ready` | Normalize names and actual availability; don't advertise unimplemented workflows. |
| Search request | `{query, domain, top_k<=20, quality, duplicate_policy}` | `SearchSpec`: `query_raw`, `top_k<=10`, `quality_mode`, `collapse_duplicates`, corpus IDs and other fields; extra fields forbidden | Translate and align limits; enforce canonical server limits. |
| Search response | `{records:[...]}` | `SearchResult.hits`, ranks, versions and source IDs; no full raw record packet | Fetch authorized original snapshots and normalize record cards; retain relevance metadata. |
| Source lookup | Query parameter `corpus_version` | `GET /records/{domain}/{source_id}` requires UUID `corpus_id` | Pass immutable corpus ID; retain it on every record/support/pin. |
| Record card/drawer | `fields`, `corpus_version`, `source_sha256` | `RecordSnapshot.original_fields`, `corpus_id`, `source_file_sha256`, `field_sha256`, raw fields | Render original fields; distinguish file hash from cited field hash. Facility ACTION is null. |
| Message POST | `{message, model, search_spec, idempotency_key, expected_revision}` | `MessageRequest`: `{text, idempotency_key, expected_revision}` | Freeze model/search selection location; adapt payload rather than sending forbidden extras. |
| Session restore | `revision`, `records`, `pins`, `board:{known,reported,missing}`, `active_run:{run_id}`, messages with `kind` | `SessionSnapshot`: `state_revision`, flat typed board items, `answers`, `active_run_id`; generic message dicts | Define one snapshot/restore adapter, including pins and evidence packets. |
| Run creation | `{run_id, session_revision}` | Workflow implementation absent locally; response contract needs agreement | Freeze response and revision semantics. |
| Answers | `findings`, `historical_actions`, `contrasting_cases` arrays | `AnswerEnvelope.claims` with `claim_type` | Group canonical claims by type for the existing UI. Keep only released/validated envelopes. |
| Actions | Uppercase strings or objects with `type`; POST uppercase action | Lowercase `action` enum; AllowedAction objects carry parent and `state_revision` | Normalize names while preserving parent/revision authorization. |
| Visual refs | Objects with `asset_id`, caption, applicability, source refs | `AnswerEnvelope.visual_refs` is a list of strings | Freeze ID resolution and reviewed context endpoint; never treat illustrative SVG as approved model geometry. |
| SSE event data | See next section | `PublicEvent.data` is a dict; exact per-event payloads not frozen here | Agree fixtures and versioned payload schemas. |

In this inspected checkout, `api/routes/workflows.py`, `maintenance/agent.py`, and `maintenance/session_repository.py` are absent. Kushaan may have additional work elsewhere. Retrieval readiness alone does not establish a working copilot.

## 7. Existing API and event seam

Client API prefix: `/api/maintenance/v1`, credentials `same-origin`.

The browser adapter expects capabilities; session create/list/restore; message/action creation; search; original records; run cancellation/SSE; version-preserving pins; upload attachments; Markdown handover export. See `api-client.mjs` for exact paths and methods. Not all of those routes exist in the inspected backend.

P1 composition discovers `api.routes.workflows.router` and optional async `startup(app)` / `shutdown(app)`. Use that seam rather than introducing a second app. Available services include `app.state.pool`, settings, identity signer, search engine, record service, pattern/comparison/sensitivity services. Read P1's handoff for full scope/auth contracts.

The current controller uses these event payloads:

- `query_interpreted`: `data.query`, `domain`, `applicability`.
- `tool_started`: `tool_call_id`, `tool_name`, `args`.
- `tool_completed`: matching call/name, `summary`, `result`, optional `error`.
- `evidence_ready`: `data.records` (normalized source packets).
- `board_updated`: `data.board` (currently grouped view model).
- `answer_validated`: `data.answer` (currently normalized answer view model).
- `run_failed`: optional `data.message`; `run_cancelled`, `done` terminate UI activity.

SSE envelope is `protocol_version='maintenance/v1'`, run UUID, positive monotonic integer sequence, event type, timestamp, data. Wire SSE `id` must equal sequence and wire `event` must equal type. Client skips duplicates, rejects gaps, and reconnects with `GET .../events?after=N`; subscriptions must not create new inference. Persist events before emission. Buffer drafts and never stream rejected or unvalidated answer text.

## 8. How to integrate evidence into the aircraft red box

For the researched source hierarchy and proposed hypothesis context packet, read [hypothesis-context-research.md](docs/p2/hypothesis-context-research.md). This is a proposal, not implemented functionality; it documents FAA/OEM/incident sources, access/applicability limits, separate technical-reference retrieval and validation requirements.

Currently there is no live log-to-internal-part binding. `airframe-mapping.mjs` maps user text to exterior IDs. `wing-profiles.mjs`, `airframe-profiles.mjs` and `issueScenario()` provide static educational context. They must not become authoritative evidence merely because a matching record is returned.

Agree a reviewed catalog and mapping revision with P1. Preserve existing exterior IDs (`seg-wing-l-flaps`, etc.) or provide an explicit migration; local profile arrays use numeric callout indices, which are not durable backend component identifiers yet.

Then design a typed payload containing: exterior component ID, reviewed internal-part ID, reported symptom, fetched record/claim IDs, exact source supports, mapping basis/confidence status, unknowns and applicability. Historical evidence, user report and educational progression need distinct labels. The backend should never supply executable markup or invented SVG coordinates.

Show exact cited record detail when available; otherwise say the internal source is unknown. A matching wing/engine word is insufficient to conclude a failed track, bearing or seal. Future complications need separately attributed educational/documentary support; log similarity cannot establish inevitability, time-to-failure or repair instructions. Keep speculative/HYPOTHESIS output separate from evidence mode.

## 9. Suggested dependency-ordered integration slice

1. Compare latest backend and frontend branches; preserve both and resolve contract changes jointly under the owner split.
2. Fix the product route and same-origin serving. Confirm capabilities accurately report readiness.
3. Freeze request/response/event fixtures and implement the view-model adapter for capabilities, search, records, sessions, answers and actions.
4. Wire real search and immutable original-record lookup; prove a citation opens exact original text and field hash. Unicode offsets use code points (`Array.from()` in JS), not UTF-16 indexes.
5. Add/finish server-owned sessions and one-live-run workflow, scoped search/get tools, real provider integration, structured answers and evidence gate. Persist a validated answer transactionally before emitting it.
6. Prove positive and unsupported/refusal queries on real data. Distinguish unavailable service from no relevant evidence.
7. Test ownership isolation, revision/idempotency conflicts, cancellation, SSE replay without duplicate inference, refresh/restart restoration, facility null ACTION and untrusted text rendering.
8. Integrate reviewed evidence-to-component mapping/red-box detail. Preserve the user's approved layout and defer unrelated answer-design changes.
9. Validate a fresh non-demo browser flow; remove/condition remaining preview-specific sidebar labels and demo-only text in live mode. Some current navigation text and the logo link still explicitly point to demo; audit those before release.

No deployment or live end-to-end/provider validation is claimed by this frontend work.

## 10. Verification and commit trail

The branch includes the original feature series through `654c1dc`, handover commit `caf2be3`, and the regional-cutaway update documented in `docs/p2/regional-cutaways.md`. Read the current files and branch HEAD for the latest baseline. Earlier commits on the same branch:

- `738100b`: initial component explorer and conditional oil-loss view.
- `248a695`: sidebar, palette and guided UI overhaul.
- `3e0f006`: one input, concise flow, internal issue context and animations.
- `ca6fb67`: larger 33-region aircraft, wing mention mapping and compact internal layout.
- `654c1dc`: six distinct wing cutaways/parts and selected-part explanation.

Run from the repository root:

```powershell
node --test tests/ui/airframe-mapping.test.mjs tests/ui/airframe-profiles.test.mjs
node --check api/static/maintenance/maintenance-ui.mjs
node --check api/static/maintenance/component-explorer.mjs
node --check api/static/maintenance/wing-profiles.mjs
git diff --check
```

Ten Node tests passed after the regional-cutaway update. All ten new regional views were opened in the browser, and new nose/rudder demo results and selected-part context were checked. Browser checks covered single issue submission, citations, directory/settings, six wing profiles, spoiler mouse selection, keyboard callouts, selected-part updates, wing side highlighting, animation styles, and 390/1440 px layouts without horizontal overflow or observed console errors. These are frontend/demo checks, not live backend acceptance. Reduced-motion overrides were reviewed in CSS.

Screenshots: `docs/p2/previews/aircraft-explorer.png`, `compact-wing-detail.png`, `flap-cutaway.png`, `nose-cutaway.png`, `rudder-cutaway.png`, plus earlier previews. P1's older retrieval/evaluation reports remain under `docs/p1/`; do not present those as new Supabase or agent validation.

## 11. Pasteable context for Kushaan's agent

> Integrate your latest Supabase/retrieval/backend work with the existing frontend on person-2-agent-experience. Read INTEGRATION_HANDOVER.md first, especially the contract mismatch table. Preserve the approved single-input flow, teal design, 33-region aircraft, distinct wing profiles and conditional evidence boundaries. Coordinate shared-contract and app-composition changes rather than fitting the server to synthetic demo payloads. Start with same-origin serving and a canonical API-to-view-model adapter, then prove real search, original cited records, session/run/SSE restoration and a validated answer/refusal. The red component panel is static educational context today and needs an explicit reviewed mapping/evidence payload; do not treat its candidate highlights as confirmed diagnoses. Report exactly what is integrated/tested and what remains pending. Do not copy secrets, private sessions, raw datasets or embeddings into commits.
