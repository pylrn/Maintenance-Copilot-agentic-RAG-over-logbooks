# NexAI Hackathon 2026: Maintenance Copilot (Problem Statement 1.3)
## Master Project Handover & Agent Onboarding Guide

---

### 1. Project & Hackathon Context
- **Hackathon:** NexAI 2026
- **Problem Statement 1.3:** *Maintenance Copilot — Agentic RAG over Logbooks (Aviation Maintenance)*
- **Core Challenge:** Aviation maintenance logbooks consist of noisy, abbreviation-heavy, terse unstructured text (`IDENT`, `PROBLEM`, `ACTION`). The system must perform **evidence-grounded retrieval**, citing exact original record fields, without hallucinating repair success, aircraft models, or unsupported procedural advice.
- **Project Name:** **Maintenance Atlas**
- **GitHub Repository:** [https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks.git](https://github.com/pylrn/Maintenance-Copilot-agentic-RAG-over-logbooks.git)
- **Primary Branches:**
  - `main` (production-ready synchronized baseline)
  - `person-2-agent-experience` (Person 2 working branch)
  - `person-1-retrieval-platform` (Person 1 working branch)
- **Local Working Directory:** `C:\Users\Vansh\Desktop\NexaI`

---

### 2. Team Split & Ownership
The project is strictly split into two complementary roles:

#### Person 1 (Kushaan) — Data, Retrieval, Platform & DB
- **Scope:** Ingestion pipeline, BM25 Okapi lexical indexing, BGE embeddings (`BAAI/bge-small-en-v1.5`), Reciprocal Rank Fusion (RRF), PostgreSQL 17 + pgvector schema and migrations, Supabase integration, search routes (`/search`, `/records`), and evaluation scripts.
- **Reference Doc:** `docs/work-split/PERSON_1_DATA_RETRIEVAL_PLATFORM.md`

#### Person 2 (Vansh) — Agent Harness, UI, Visuals & Investigation Workflows
- **Scope:** Adapted Talent Atlas frontend shell, PydanticAI / Gemini / DeepSeek LLM harness, evidence validation gate (`AnswerEnvelope`), session history repository, SSE event stream, investigation board (Known / Reported / Missing), action modes (`CHALLENGE`, `DISTINGUISH`, `SENSITIVITY`, `HYPOTHESIS`), and the **2D Interactive Airframe Structural Locator with Component Drill-Down**.
- **Reference Doc:** `docs/work-split/PERSON_2_AGENT_UI_WORKFLOWS.md`

---

### 3. Current Implementation Status & What Has Been Built

#### A. Frontend Architecture (`api/static/maintenance/`)
1. **Design Tokens & Palette:**
   - Warm paper canvas (`--bg: #f8f6f1`, `--paper: #ffffff`), deep navy navigation (`#081726` / `#0f2b46`), rust/orange accents (`--rust: #c25f38`), Archivo/Newsreader/IBM Plex Mono typography.
2. **Interactive Top-Down Airframe Locator (Full-Width, 20 Segments):**
   - Placed prominently below the AI search box.
   - 20 distinct structural segments: Radome, Forward Avionics, Cockpit, Cabin sections, Center Wing Box, Left/Right Wings (Leading Slats, Main Spar/Tank, Flaps/Ailerons), Left/Right Engines & Pylons, Horizontal Stabilizers, and Vertical Fin/Rudder.
   - **Interactive Cyan-Blue Hover:** Segments highlight on mouse hover (`fill: #e0f2fe; stroke: #0284c7;`).
   - **Real-Time Fault Alert Highlighting:** Typing or submitting queries (e.g. *"cylinder #2 intake leak"*, *"right wing cracks"*, *"cockpit pfd"*) triggers instant **Aviation Emergency Red (`#dc2626`)** on the affected aircraft component with an alert badge.
3. **Interactive Structural Drill-Down Engine:**
   - Clicking a highlighted or selected component transitions into a dedicated **Internal Structural Inspection View**:
     - **Wing Drill-Down:** Shows internal ribs, main spars, pylon attachment, and localized fracture lines/cracks.
     - **Engine Turbofan Drill-Down:** Shows Bypass Fan, LP Compressor, HP Compressor & Coolant Line Junction (pinpointing coolant/fuel leaks), Combustor, and Turbine.
     - **Avionics Drill-Down:** Displays Cockpit PFD/Nav displays, bus links, and tripped breaker indicators.
   - Includes full telemetry readouts and a "← Back to full airframe" navigation button.
4. **Offline Demo Adapter (`demo-adapter.mjs`):**
   - Self-contained fixture engine running with real MaintNet records (`100009`, `100086`, `100037`, `100015`, etc.), allowing interactive testing on `http://localhost:8765/?demo=1` before database connection.

#### B. Backend & Agent Core (`maintenance/` & `api/`)
1. **Config & AI Provider Setup (`maintenance/config.py`):**
   - Integrated settings supporting Google Gemini (`gemini-2.5-flash`) via `GEMINI_API_KEY` in `.env`, as well as DeepSeek (`deepseek-flash`).
2. **Contracts & Evidence Gate (`maintenance/contracts.py`):**
   - `SearchSpec`, `RecordSnapshot`, `Claim`, `Support`, `AnswerEnvelope`, `HypothesisEnvelope`, and event taxonomy.
3. **Database Migrations (`db/migrations/`):**
   - `001_core.sql` through `006_validate_state.sql` covering sessions, runs, evidence snapshots, computed receipts, and claims.
4. **P1 Retrieval Integration:**
   - Ingestion scripts (`scripts/ingest.py`, `scripts/build_indexes.py`) and retrieval engine (`maintenance/retrieval/engine.py`) merged from Kushaan's branch.

---

### 4. Key Files Directory Reference

| File Path | Description |
|---|---|
| `api/static/maintenance/index.html` | Core UI structure: topbar, AI input, 20-segment 2D plane schematic, drill-down container, investigation workspace |
| `api/static/maintenance/maintenance.css` | Complete stylesheet for the airframe locator, drill-downs, cards, and modal components |
| `api/static/maintenance/maintenance-ui.mjs` | Primary browser controller: SSE subscriber, fault detection parser, drill-down renderer |
| `api/static/maintenance/api-client.mjs` | REST client and durable SSE streaming client |
| `api/static/maintenance/demo-adapter.mjs` | Simulated offline backend adapter with historical MaintNet records |
| `api/static/assets/engine-concept.svg` | Detailed aircraft reciprocating engine schematic |
| `maintenance/config.py` | Pydantic Settings supporting Gemini, DeepSeek, and retrieval limits |
| `maintenance/contracts.py` | Pydantic 2 schemas for queries, records, claims, supports, and envelopes |
| `docs/prompts/maintenance_system_prompt.md` | Authoritative system prompt for evidence-gated answers |
| `docs/work-split/` | Explicit work breakdown files for Person 1 and Person 2 |
| `IMPLEMENTATION_PLAN.md` | Full 28-page technical specification and roadmap |

---

### 5. Running the Project Locally

```powershell
# In C:\Users\Vansh\Desktop\NexaI
# Start the frontend preview in demo mode:
python -m http.server 8765 --directory "C:\Users\Vansh\Desktop\NexaI\api\static\maintenance"

# Open in browser:
# http://localhost:8765/?demo=1
```

---

### 6. Immediate Next Steps for the Incoming Agent
1. **Supabase & Real DB Connection:**
   - Person 1 is wiring the 6,000+ MaintNet records into Supabase/PostgreSQL.
   - Once the DB connection string is set in `.env`, mount the FastAPI backend (`uvicorn api.main:app --port 8000`) and switch the UI from `?demo=1` to live API mode (`/maintenance/`).
2. **PydanticAI Agent Completion (`maintenance/agent.py` & `agent_run.py`):**
   - Connect `search_records` and `get_records` tools to the live retrieval engine.
   - Enforce the evidence gate so that LLM output is parsed into structured claims validated against raw log spans before the `answer_validated` SSE event is emitted.
3. **Commit Workflow:**
   - Make atomic, meaningful commits to `person-2-agent-experience` or `main` and push to remote.
