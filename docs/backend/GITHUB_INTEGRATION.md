# Local GitHub Main Integration Report

## Integration Main SHA
- **Fetched & Merged Target**: `b66fe7a` (`Merge branch 'person-2-agent-experience'`)
- **Remote Origin**: `https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks.git` (main branch, fetched locally without remote mutations)
- **Local Merge Commit**: Clean local integration on branch `gdd/workflow-jsonb`

## Resolved Paths & Merging Strategy

### 1. `maintenance/config.py`
- **Resolution**: Preserved hardened backend `Settings` wholesale.
- **Details**: Maintained `gemini_base_url`, `gemini-3.8-flash`, `deepseek-flash`, complete `model_allowlist`, and strict production validation (`secure_production`). Incoming main did not introduce new runtime settings required by backend workflows.

### 2. `config/component_catalog.json`
- **Resolution**: Merged existing reviewed components with new incoming catalog entries while preserving metadata provenance.
- **Details**: Preserved all 10 reviewed aviation components (`cylinder_assembly`, `intake_system`, `intake_gasket`, `intake_pipe`, `rocker_cover`, `exhaust_system`, `crankcase`, `baffle_assembly`, `fuel_system`, `oil_system`) with original `review_status: "reviewed"` and FAA citations. Incorporated incoming additions (`engine_general`, `intake_manifold`, `exhaust_manifold`, `baffle_cooling`) retaining their original incoming provenance (`review_status: "approved"`, no unsupported FAA citations).

### 3. `config/visual_mappings.json`
- **Resolution**: Preserved reviewed visual mappings and schema compatibility with `VisualService`.
- **Details**: Retained `asset_id: "engine_concept_piston_2d"` (required by `/api/maintenance/v1/visuals/engine_concept_piston_2d` and `VisualService.get_asset_info()`). Added dual keys (`hotspot_id` and `node_id`) across all mapping entries. Existing entries preserve `source: "FAA-H-8083-32B"` and `reviewer: "human_reviewed"`; incoming new entries preserve `reviewer: "person-2"` without unsupported sources.

### 4. `api/static/assets/engine-concept.svg`
- **Resolution**: Preserved reviewed schematic SVG while adding alias IDs for incoming node mappings.
- **Details**: Maintained `class="engine-concept-svg"`, `data-component-id` tags, and all existing nodes (`node-cooling-baffles`, `node-crankcase`, `node-oil-system`, `node-cylinder-bank`, `node-rocker-cover`, `node-intake-manifold`, `node-intake-pipe`, `node-intake-gasket`, `node-exhaust-manifold`, `node-fuel-injector`). Added nested alias IDs (`node-cylinder`, `node-rocker`, `node-intake`, `node-exhaust`, `node-baffle`) so that all node identifiers referenced across `visual_mappings.json` exist and validate.

## Intentional Retained Assets
- **Canonical `/maintenance` Route & Legacy Assets**: Kept `api/static/maintenance.html`, `maintenance.js`, and `maintenance.css` as the active canonical UI served by `/maintenance`.
- **New Modular UI Assets**: Preserved incoming modular UI files in `api/static/maintenance/**` (`index.html`, `maintenance-ui.mjs`, `api-client.mjs`, `demo-adapter.mjs`, `maintenance.css`, `talent-base.css`) and `api/static/assets/aircraft-silhouette.svg` for standalone inspection and retrieval UI continuation.
- **Incoming Documentation**: Preserved `AGENT_ONBOARDING_HANDOVER.md`, `docs/p2/dependency-requests.md`, and `docs/p2/schema-requests.md`.
- **Backend Integrity**: `api/main.py`, retrieval engine, contracts, database pool/migrations, and `maintenance/session_repository.py` remained untouched.

## Remaining Live UI Adapter Mismatches

The modular UI assets in `api/static/maintenance/` contain known API mismatches against the live FastAPI backend contracts:

1. **`models`**:
   - *UI Behavior*: `maintenance-ui.mjs` submits `model: $('agentModelSelect').value`.
   - *Backend Contract*: Backend selects and enforces allowed models via backend `Settings` and capabilities configuration; client-driven arbitrary model strings are ignored or rejected.
2. **`revision`**:
   - *UI Behavior*: `maintenance-ui.mjs` does send `expected_revision`, but reads `state.session.revision` (e.g. `expected_revision: state.session.revision`). Because the backend snapshot contract exposes `state_revision` instead of `revision`, `state.session.revision` evaluates to `undefined`, resulting in an omitted/undefined `expected_revision` parameter over the wire.
   - *Backend Contract*: `MessageRequest` and action contracts require a valid non-negative integer `expected_revision: int` for optimistic locking and race condition prevention.
3. **`record corpus_version`**:
   - *UI Behavior*: `api-client.mjs` requests `/records/{domain}/{source_id}?corpus_version={corpus_version}`.
   - *Backend Contract*: `api/routes/records.py` defines the endpoint with query parameter `corpus_id: UUID`.
4. **`messages`**:
   - *UI Behavior*: `maintenance-ui.mjs` issues `POST /sessions/{id}/messages` with `{ message: text, model: ..., search_spec: ..., idempotency_key: ..., expected_revision: ... }`.
   - *Backend Contract*: `MessageRequest` expects field `text: str` (not `message: str`).

## Test Verification
- `PYTHONPATH=. .venv/bin/pytest -q tests/ui/test_ui.py tests/workflows/test_workflows.py`: **3 passed**
- `PYTHONPATH=. .venv/bin/pytest -q tests/workflows/test_jsonb_storage.py`: **3 passed**
- `.venv/bin/ruff check maintenance/config.py maintenance/session_repository.py tests/workflows/test_jsonb_storage.py`: **Clean (0 errors)**
- SVG Node Verification: Confirmed `node-intake-gasket` and all referenced visual mapping nodes exist in `api/static/assets/engine-concept.svg`.
