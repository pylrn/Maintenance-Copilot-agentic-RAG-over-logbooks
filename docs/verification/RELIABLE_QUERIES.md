# Reproducible evidence and abstention queries

Use Aviation domain, Evidence mode, and **extractive/v1** for the exact deterministic behavior verified here. Ten queries were each run three times against the local backend: **30/30 passed**, with original source quote offsets and field hashes checked. No model API calls were made. Tests: **131 passed, one skipped**.

These are historical-record findings, not proof of cause, repair effectiveness or aircraft applicability. They do not provide certified repair advice. Exact source ranking can change when corpus/index versions change.

## Evidence examples

### `intake leak`

Expected status: `supported_historical`.

Actual summary:

> Historical record aviation:102838 reports: "#2 INTAKE HAS LEAK.". Its recorded action is: "REMOVED & REPLACED INTAKE GASKET.".

### `baffle crack`

Expected status: `supported_historical`.

Actual summary:

> Historical record aviation:100614 reports: "CRACK IN RIGHT FRONT BAFFLE.". Its recorded action is: "STOP DRILLED CRACK.".

### `baffle cracking`

Expected status: `supported_historical`.

Actual summary:

> Historical record aviation:103361 reports: "#3 BAFFLE CRACKED.". Its recorded action is: "STOP DRILLED CRACK IN #3 ENG BAFFLE.".

### `R/H engine forward alternator attachment bolt loose.`

Expected status: `supported_historical`.

Actual summary:

> Historical record aviation:100033 reports: "R/H ENG FWD ALT ATTACH BOLT LOOSE.". Its recorded action is: "SECURED ALT ATTACH BOLT & RESAFETIED.".

### `#3 brake is missing a screw.`

Expected status: `supported_historical`.

Actual summary:

> Historical record aviation:100045 reports: "#3 BRAKE MISSING SCREW.". Its recorded action is: "REPLACED SCREW.".

## Abstention examples

Each of the following returned `insufficient_evidence` with **zero claims, zero answer visual references and zero allowed follow-up actions** in all three passes:

- `Right main gear brake pedal feels soft and spongy`
- `CYL #99 intake leak`
- `baffle crack with unfamiliar actuator failure`
- `What is the approved torque specification in ft-lbs for the intake flange?`
- `Is the aircraft safe to fly after this intake leak?`

Expected visible explanation for non-procedural unsupported complaints:

> Insufficient evidence: retrieved candidates do not establish a matching complaint in the authorized records. This does not prove that the fault is absent or identify a repair.

The conclusion says:

> No evidence found for this complaint in the historical records.

Approved-specification and operational-clearance requests additionally disclose that historical logs do not establish that authority. The absence of a supported answer is not evidence that a real-world fault is absent.

## What is and is not established

The new endpoint regression passes completely. The earlier fixed-packet model benchmark remains **mixed**, not all favorable: full Flash was quota-blocked, and some Lite attempts timed out or returned provider errors. Those failures are retained in `SYNTHESIS_BENCHMARK.md`; deterministic fallback is not counted as model success. Switching to a different model or generation mode may change selected source records or abstention behavior. A longer timeout might improve completion rate but has not been established as a quality/latency improvement here.

The recent fix recognizes “cracking” as the same symptom as “crack/cracked.” Broader known limitations (component/facility vocabulary, contextual follow-ups, Challenge/Sensitivity, visual specificity) remain outside this targeted regression. This is a versioned acceptance suite, not a guarantee for arbitrary queries.

Reproduce locally, creating isolated verification sessions:

```sh
.venv/bin/python scripts/verify_reliable_queries.py
```

Raw outputs and run IDs: `synthesis-results/reliable-query-regression.json`.
