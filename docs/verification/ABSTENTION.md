# Evidence-mode abstention verification — 22 October 2026

## Implemented behavior

Search candidates are not automatically proof. Before Evidence-mode synthesis, the backend selects whole records whose original PROBLEM/DESCRIPTION covers every recognized complaint facet: component, symptom, and any requested laterality or number context. A conflicting or missing facet rejects that record. Matching terms from separate records cannot be combined to establish a match. ACTION text cannot establish a problem match. Only actions belonging to accepted records enter synthesis and claim rendering.

No accepted record means deterministic `insufficient_evidence`, zero claims, zero answer visual references, zero allowed follow-up actions, and no LLM request. Retrieved candidates remain inspectable in source evidence; their presence does not make the answer supported. Explicit insufficient-evidence rendering now also takes precedence over nonempty candidates.

Existing exact-quote, offset and source-hash validation still runs before answer persistence/release. A supported result means matching historical logs, not approved instructions, causal proof, or applicability to a particular aircraft.

## Five reusable queries

| Query | Expected status |
|---|---|
| intake leak | supported_historical |
| baffle crack | supported_historical |
| Right main gear brake pedal feels soft and spongy | insufficient_evidence |
| CYL #99 intake leak | insufficient_evidence |
| What is the approved torque specification in ft-lbs for the intake flange? | insufficient_evidence |

Use Aviation domain and Evidence mode. The first two are positive controls: the gate must preserve actual historical evidence rather than refusing everything. The third reproduces the misleading earlier brake response. The fourth tests explicit cylinder mismatch. The fifth tests an unsupported approved specification.

## Verification evidence

- `PYTHONPATH=. .venv/bin/python -m pytest tests/agent/ -q`: **48 passed** in the canonical checkout; the isolated worktree run had 47 passed and one database-dependent test skipped.
- `.venv/bin/python scripts/verify_abstention.py`: five queries with Gemini and the same five with `extractive/v1`, **10/10 passed** on the local backend. A separate Python environment with httpx was used for this run.
- All six live abstentions had zero claims, visual references and allowed actions, plus the deterministic no-evidence conclusion.
- Live abstention latency: **0.063–0.209 seconds**. Positive Gemini runs: **2.531s** and **12.136s**. The latter reached the model timeout and successfully returned the cited extractive fallback. Positive extractive runs: **0.105–0.117s**.
- `ABSTENTION_RESULTS_2026-10-22.json` contains exact queries, model selection, statuses, durations, run/session IDs, summaries and released source quotes.
- Unit coverage includes wrong side, absent side, wrong cylinder, negation, unsupported vocabulary, symptoms split across records, action-only matches, same-record action selection, explicit rendering abstention, and model failure. Runner tests verify no LLM calls for abstentions.

Reproduce against the running local backend:

```sh
PYTHONPATH=. .venv/bin/python -m pytest tests/agent/ -q
.venv/bin/python scripts/verify_abstention.py --base-url http://localhost:8000
```

The live script intentionally creates ten isolated verification sessions. It fails on unexpected status, nonempty abstention claims/actions/visuals, missing positive citations, or a failed run.

## Limits

This is a conservative vocabulary-based complaint gate, not a proof of universal semantic correctness. Unrecognized components/symptoms and missing identity qualifiers can cause false abstentions. An abstention means the fetched authorized evidence does not establish support; it does not establish that the fault never occurred or that no matching record exists elsewhere. The live suite establishes the five listed behaviors, not every possible natural-language query. Non-Evidence agent modes retain their existing policies.
