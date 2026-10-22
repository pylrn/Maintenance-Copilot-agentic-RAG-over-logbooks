# Live Langfuse verification — 22 October 2026

Verified against the locally running Atlas backend and the private Tokyo `nexai` project. Credentials are in ignored `.env.langfuse`, not in this report or the image. Setup/dependency work was reviewed from GDD checkpoint `dd1e99f`; core tracing was completed and reviewed in a separate checkout. Integrated source commits: `63c541c`, `5017d4f`, `87e7edb`. Concurrent Antigravity fixes through `0299716` were preserved.

## Results

- Credential authentication: HTTP 200 for the intended project.
- Langfuse SDK: 4.18.0; requirements hashed and uv lock checked.
- Focused tests: 14 passed, 1 database-profile-dependent workflow test skipped. The successful live persisted run below independently exercised workflow persistence.
- Python lint, JS syntax and staged whitespace checks passed.
- Live health: ready/app/retrieval/database/workflows all true, no startup errors.
- Direct aviation search: HTTP 200, 6 hits, first record aviation:103578; 94 ms client HTTP in this spot check. Search trace `6d457868116fb94a87339de14317556d` returned in SearchTrace.telemetry.
- Real Gemini investigation run `bdb4257f-01a4-41e4-8513-419bd6c0575b` completed with answer_validated followed by done and one persisted answer.
- Remote observations API confirmed 18 observations for trace `a10cfcf1a8275fc2813132cefdcaf0e9`. Logical agent root and all child/parent links verified; session linkage verified.
- Two successful generations reported actual `gemini-3.5-flash-lite`, 5,440 input tokens and 2,888 output tokens total. Langfuse calculated $0.008852 across them; the application did not invent a cost estimate. The complete run lasted 8.63 seconds in the dashboard.
- Remote input/output fields were absent for every observation. Error tests confirmed raw exception text/events are not captured. Full stage timings/counts are present; use Observations API expand_metadata for stage_timings_ms/stage_counts because ordinary API reads truncate long metadata previews at 200 characters.
- Chrome verified the product Telemetry link and an actual per-investigation trace link; no browser console errors in that flow. A UI extractive run also completed with trace `45c26cd11b9d010ffb8c8a688e98d1c1`.
- Langfuse Tree and Timeline views displayed actual retrieval/tool/generation/guardrail/persistence observations, durations, tokens and costs. Graph view is available on the same trace page.

[Open the verified investigation trace](https://jp.cloud.langfuse.com/project/cmvjf4dgo007iad0i5g0mw7f2/traces/a10cfcf1a8275fc2813132cefdcaf0e9)

## Build/runtime detail

The full Docker build encountered a network read timeout while re-downloading the unchanged uv 0.7.3 installer. For this local run, an incremental image was built from the existing maintenance-atlas image, installed the exact updated hashed requirements, and copied current source/config/prompt files. The 12 added dependencies installed successfully. Runtime image SHA: `84f26af8e21eb8dd5563d8b024ea4858c6e24e565ec06aa6ea6d4dc9d2c04271`.

The standard repository Dockerfile remains the clean-build recipe; it needs working package-download connectivity. This verification does not claim that the failed full download/build succeeded. The running app uses the existing local DB/provider setup plus compose.langfuse.yaml; it does not switch databases or disable the configured generation key. No models were downloaded.

These are functional spot checks, not a broad retrieval-quality evaluation, load test or proof that every pre-existing application feature is correct. Validation spans identify the actual claim/span-check scope, not independent certification of all generated synthesis or educational prose.
