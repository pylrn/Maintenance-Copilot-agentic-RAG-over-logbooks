# Prompt/model benchmark — 22 October 2026

## Outcome

The active Evidence prompt now uses `evidence-selection/v2`: strict source selection, not unchecked generated prose. The harness checks fetched evidence IDs, original field types, same-record action pairing, and reconstructs visible summaries/conclusions for validation. Model-written unsupported summaries cannot bypass the quote validator. The old CRACK/LEAK-to-operational-check inference is removed. Unknown conjunctive complaint clauses and unsupported operational guarantees now abstain conservatively.

The adapter sends the selected model unchanged. It no longer silently maps full Flash models to Flash-Lite. Automatic provider/model fallback is off. Per-answer generation metadata and the UI distinguish requested/effective model, validated selection, and extractive fallback/error reason. Explicit model abstention is preserved. Default reasoning effort remains `low`: this small trial did not establish a benefit from switching to `minimal`.

## Fixed expected-output benchmark

Eight synthetic evidence packets were specified before calling providers in `eval/synthesis/golden.json`: direct intake/action pairing; crack without inferred operational check; wrong-side brake; wrong cylinder; unsupported extra clause; operational clearance; distinct records without inferred recurrence; facility description without fabricated ACTION.

These isolate model/prompt behavior from retrieval. They do not establish end-to-end corpus recall, and were not a randomized model comparison. Attempts within the twelve-second production generation budget are recorded below; timeouts/provider failures are not quality passes.

| Requested model / effort | Attempts | Correct validated decisions | Timeouts | Other errors | Median successful latency |
|---|---:|---:|---:|---|---:|
| gemini-3.8-flash / low | 1 | 0 | 0 | 1 quota rejection; remaining cases skipped | unavailable |
| gemini-3.5-flash / low | 1 | 0 | 0 | 1 quota rejection; remaining cases skipped | unavailable |
| gemini-3.5-flash-lite / low | 8 | 5 | 3 | 0 | 4.38s |
| gemini-3.1-flash-lite / low | 8 | 5 | 2 | 1 provider error | 5.94s |
| gemini-3.1-flash-lite / minimal | 8 | 4 | 2 | 2 provider errors | 4.35s |

All fourteen successful model selections matched the predefined expected decision. The availability failures matter: this is not an 8/8 reliability result for any model. Full Flash quality cannot be compared while quota-blocked. Model catalogue availability was verified separately via HTTP200; that does not establish remaining request/day quota. Thinking-token usage was absent in the successful provider responses and remains unknown.

The benchmark calls the selector directly with even incompatible evidence to test prompt decisions. On model failure its standalone source-rendering fallback validates citation/prose structure, but that **does not mean the raw incompatible benchmark packet supports the complaint**. Production performs the complaint gate first. Do not count standalone fallback validation as end-to-end answer correctness.

## Rate-limit handling

One request in flight; initial65-second cooldown for each benchmark process; rolling caps of2 requests/minute/fullFlash,4/Lite and4 globally. Max8000 input UTF-8 bytes including schema plus3072 output budget yields a conservative44,288 token/minute bound for this process. It stopped each quota-rejected model after one request, with no retry and no model substitution. Three sequential benchmark processes issued26 generation attempts total:24 Lite and2 fullFlash probes. Quota responses can still occur from daily exhaustion or account activity outside this process; pacing does not create quota.

## Verification and reproducibility

- `PYTHONPATH=. .venv/bin/python -m pytest tests/ -q`:130 passed,1 skipped.
- `node --test tests/ui/*.test.mjs`:10 passed.
- `node --check api/static/maintenance/maintenance-ui.mjs`:passed.
- Raw fixed-evidence runs are in `synthesis-results/`; each records individual decisions, IDs, token usage, latency, failure reason and released text.
- `synthesis-results/endpoint-extractive.json`: seven queries repeated in two extractive passes against the deployed local backend,14 cases, zero model calls. Includes original five controls plus mixed unsupported clause and operational clearance.
- The same production prompt/schema were used in the three model runs. No model parameter was changed silently, no provider failures were discarded from the reports, and there were no hidden retries.

To repeat a paid/quota-consuming benchmark intentionally:

```sh
PYTHONPATH=. .venv/bin/python scripts/benchmark_synthesis.py --live \
  --models gemini-3.8-flash gemini-3.5-flash-lite \
  --reasoning-effort low --cooldown 65 \
  --output /tmp/synthesis-comparison.json
```

The pacing guard requires at least60 seconds initial cooldown. Never run benchmark processes concurrently. The private env file is read server-side; credentials are not included in reports.

## Remaining limits

This change addresses prompt/model identity and synthesis grounding. The broader audit's narrow component/symptom vocabulary, engine/facility recall, conversational referent resolution, canned Challenge, Sensitivity route, hypothesis reference grounding and component visual specificity are separate work. More reasoning cannot repair a record rejected before generation or a hard-coded action response. The generated text is deliberately quote-based; fluent novel factual paraphrases are not currently accepted as verified synthesis.

Full harness flow, trust boundaries and settings: `HARNESS_AND_PROMPT.md`. Actual normal loop: authorize → retrieve → fetch immutable originals → complaint gate → one structured selection → validate IDs/pairing → render source-based text → validate quotes/hashes/prose → persist → release SSE answer. No generation if insufficient; bounded deterministic fallback on provider failure.
