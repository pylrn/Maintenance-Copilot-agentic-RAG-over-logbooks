# Research: source-grounded hypotheses and possible consequences

Researched 22 October 2026, India time, for Maintenance Atlas. This is a design recommendation, not implemented backend behavior. No app code, shared contracts or provider configuration was changed.

## Recommendation

Use the model to reason over retrieved evidence and scoped technical references. Do not rely on its memorized aviation knowledge as the authority for a root cause, applicability, repair or forecast. Keep the existing evidence-only answer separate from an explicit user-requested HYPOTHESIS branch.

Build a small curated reference library first. For the hackathon, use relevant sections of current FAA Aviation Maintenance Technician handbooks plus the supplied log corpus. Add aircraft/engine-specific manufacturer material only when legitimately accessible and its model/configuration/revision applicability can be established. Keep manufacturer documents, historical incidents and generic handbooks distinguishable.

The product should answer two different questions:

1. **Possible causes:** what mechanisms could explain the reported symptom, with supporting reference passages and missing distinguishing observations?
2. **Possible consequences:** under which additional conditions might the problem have downstream effects? This is conditional mechanism explanation, not time-to-failure prediction.

Both fit the existing explicit HYPOTHESIS boundary. A server-controlled purpose such as possible_causes/possible_consequences could select the output template; this is a contract proposal for P1/P2 review, not a new client-granted authority mode.

## Official sources and what they support

| Source | What to use it for | Boundary |
| --- | --- | --- |
| [FAA Aviation Handbooks & Manuals](https://www.faa.gov/regulations_policies/handbooks_manuals/aviation) | Initial reference library: AMT General FAA-H-8083-30B, Airframe 31B, Powerplant 32B, listed as 2023 editions when checked | General instruction and system principles; not proof of a fault or applicability of a specific procedure |
| [FAA Powerplant preface](https://www.faa.gov/sites/faa.gov/files/01_amtp_front.pdf) | Confirms the handbook's educational scope and coverage of engine construction, lubrication, cooling, fuel and ignition | Use actual retrieved chapter passages for individual mechanism claims; the preface alone is not evidence for them |
| [Airbus technical-documentation access](https://www.aircraft.airbus.com/en/contact-us/get-technical-assistance) | Obtain applicable technical documentation through AirbusWorld/airnavX; MRO delegation is described on the page | Access is controlled. This research did not access the manuals or establish permission to ingest them |
| [Airbus technical-data publication](https://www.aircraft.airbus.com/sites/g/files/jlcbta126/files/2021-08/airbus-fast61-april2018.pdf) | Background on AMM, troubleshooting manuals and technical-data organization | An explanatory publication is not a current applicable troubleshooting task |
| [Lycoming technical publications](https://www.lycoming.com/contact/knowledge-base/publications) and [digital-publications explanation](https://www.lycoming.com/content/news-digital-technical-publications) | Official piston-engine source discovery: service bulletins/instructions/letters and manuals, subject to availability and access | Select actual engine family and document effectivity. Some comprehensive publications are paid. Do not assign a Lycoming model to an unknown-model log |
| [FAA Airworthiness Directives](https://www.faa.gov/regulations_policies/airworthiness_directives) | Check for documented unsafe conditions applicable to a specific product | ADs are regulations, not general advice; preserve identifiers, effective dates, supersession and effectivity. A matching symptom does not establish applicability or compliance |
| [FAA SAIBs](https://www.faa.gov/aircraft/safety/alerts/saib) | Additional official safety information and recommendations, available through DRS | FAA describes SAIBs as non-regulatory information; do not label them as ADs |
| [FAA Service Difficulty Reporting System](https://sdrs.faa.gov/) and [AC 20-109B](https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/1042240) | Supplemental historical defect/malfunction examples | Reports describe reported events. Do not use retrieved report counts as fleet failure probabilities or validated root causes |
| [NTSB CAROL](https://www.ntsb.gov/Pages/CAROL.aspx) and [investigation dockets](https://data.ntsb.gov/Docket/forms/Searchdocket) | Investigated mechanisms, factual evidence, final findings, contrasting cases | Preserve report status. Preliminary reports/factual observations are not final probable-cause determinations; a different accident is not this user's diagnosis |
| [FAA AC 43.13-1B description](https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/99861) | Supplemental inspection/repair reference where its stated scope applies | FAA limits the described material to nonpressurized areas when manufacturer instructions are absent; it is not a universal replacement for applicable manufacturer instructions |

Boeing also advertises technical documentation through [MyBoeingFleet](https://services.boeing.com/myboeingfleet-portal). The official search result was available, but direct opening returned HTTP 403 in this research; access and any actual manual content were not verified.

Do not populate a trusted library from unofficial manual mirrors or forum posts when official sources are available. Public accessibility and ingestion/redistribution rights are different questions; retain access/licensing metadata for manufacturer materials.

## Important finding for this project

The official FAA catalog now lists the B editions of the AMT handbooks. Some existing educational links in our UI point to older AC 65-15A/65-12A or 32A material. Those links were illustrative references, not a reviewed evidence library. Build the new library from deliberately selected editions and record their revisions; do not silently mix passages from old/new editions.

The complete current Powerplant PDF is approximately 205 MB. The browser tool could not fetch it because of its size. This research verified the official catalog listing, public access location and preface, but did not inspect every chapter of that edition or validate a complete chapter extraction. Download/extract selected source files locally during implementation and review the extracted pages before enabling claims.

A second important boundary: logs mentioning cylinder intake/rocker-cover components cannot be assigned a turbofan architecture because the UI draws a turbofan-like engine. Source model and configuration remain unknown in the current corpus. Maintain separate reference retrieval tags for reciprocating, turbine and generic/unknown systems. If architecture is unknown, avoid engine-specific mechanisms or ask for that information when it materially changes the explanation.

## What context to give the agent on a button click

Construct one bounded packet server-side, using the current authorized session state and a released parent answer. Do not send the entire 6,000-row corpus, whole manuals, or an unaudited history summary.

1. **Authority:** owner/session/run scope, parent answer ID/hash, state revision, authoritative mode/purpose, allowed tools, tool/model budgets. These are server-supplied fields, not values accepted from retrieved text.
2. **Reported observations:** exact user symptom, laterality, engine/cylinder numbering, fluid identity, operating context, actual readings/trends if supplied, negated observations, contradictions and unresolved ambiguity. Preserve user_report versus measured/verified origin.
3. **Configuration:** aircraft and engine family/model/variant if known, verification source, serial/configuration or modification effectivity when relevant. Explicit unknowns are valid. The selected SVG/model is not configuration evidence.
4. **Historical evidence:** a small compatible set of original fetched records, exact PROBLEM/ACTION spans, corpus IDs and field hashes; direct versus related matches, meaningful differences and incomplete text. An ACTION entry does not prove repair success.
5. **Technical reference evidence:** narrow passages about the specific system, mechanism and conditions. Every passage carries document title/ID, publisher, edition/revision, chapter/section, printed/PDF page mapping, exact original text and offsets/hash, source URL and applicability status.
6. **State and alternatives:** existing known/reported/missing board with origins, conflicting evidence, rejected alternatives and relevant earlier observations. Earlier assistant hypotheses are untrusted branch material, not known facts.
7. **Output constraints:** distinguish log report, cited technical principle and inference; identify assumptions and what would weaken each hypothesis; no invented measurements, probabilities, repair steps, settings, dispatch decisions or failure timeline.

Suggested initial budget for implementation experiments: 3–6 representative records and 4–8 technical passages, at most three candidate explanations. These are unmeasured starting values; adjust after coverage and latency tests. Add adjacent sections where a passage depends on a condition, figure or table. Drop duplicate/irrelevant hits before dropping applicability metadata.

## Suggested source and passage metadata

```json
{
  "source_type": "technical_reference",
  "authority_class": "faa_educational",
  "document_id": "stable-server-id",
  "title": "Document title",
  "publisher": "FAA",
  "revision": "verified-edition",
  "retrieved_at": "record-at-ingestion",
  "source_url": "official-url",
  "aircraft_family": null,
  "engine_architecture": "generic_or_explicit_family",
  "model_effectivity": null,
  "applicability": "generic",
  "chapter": "verified-chapter",
  "section": "verified-section",
  "printed_page": "verified-label",
  "pdf_page_index": 0,
  "passage_id": "immutable-passage-id",
  "text_sha256": "computed-from-original-passage",
  "text": "Exact extracted source text",
  "access_scope": "public_or_owner_authorized",
  "allowed_use": ["conceptual_explanation"]
}
```

Illustrative shape only: no example identifiers/page numbers above are actual citations. Real source IDs, hashes and locations are generated/verified on ingestion. Applicability generic means suitable for generic explanation, not matched to the user's aircraft.

## Retrieval and reasoning sequence

1. Authorize the click against the stored parent answer/current state. The current local 'What could follow?' toggle only reveals static text; do not quietly turn it into unrestricted web/model reasoning.
2. Resolve symptom and configuration constraints. Use the existing log search/get-record tools as needed; re-fetch the immutable corpus version behind citations.
3. Query a **separate technical-reference index**, not a blended log/manual index with unlabelled source types. Hybrid lexical+dense retrieval is suitable as an engineering starting point. Filter by access, architecture and known model effectivity before synthesis; handle unknowns explicitly.
4. Retrieve original passages (not merely search snippets), plus relevant qualifications/neighboring sections. Preserve tables, diagrams and caveats. Reject ambiguous OCR of limits/numbers rather than reconstructing it.
5. Generate bounded structured hypotheses or conditional consequence chains. For each, identify evidence, assumptions, missing observations and counter-evidence. Rank by support/relevance if useful, not invented percentage likelihood.
6. Validate source identity, current revision/applicability, exact spans and semantic support for each assertion. A real quotation does not validate an unrelated causal conclusion. Every link in a consequence chain needs either cited mechanism support or an explicit inference label and assumptions.
7. Persist the separately labelled HYPOTHESIS result and references, then release it. Candidate internal-part highlights remain unverified. Only allowlisted component IDs may be returned; never model-authored HTML/SVG or arbitrary coordinates.

Use a backend allowlisted document-ingestion pipeline rather than letting every run browse arbitrary web pages. Periodically review source updates and invalidate changed/superseded material. Do not overwrite immutable evidence used by old investigations.

## Recommended result format

Keep the user-facing output compact:

- **Possible explanation:** short mechanism statement, not a diagnosis.
- **Why it fits:** observed symptom and compatible historical-source findings, with real source refs.
- **Technical basis:** one cited reference passage; generic/model-specific applicability label.
- **Still unknown:** assumptions and missing observations that distinguish this from alternatives.
- **What could follow, if:** optional conditional chain with source support and no invented timing.
- **What weakens it:** contrary observations or source differences.

Store atomic structured claims/supports underneath the display. Do not cite a log as proof of a mechanism that only the reference describes. Distinguish 'a source documents this condition' from 'this condition exists on this aircraft'.

Example for the concept of oil loss (not a validated answer):

> User report: oil is visible near Engine 1.\n
> Historical record: display only the exact fetched complaint/action.\n
> Possible source: storage, supply or return interfaces may be considered only where retrieved applicable/general documentation supports that system layout. Exact leak origin remains unknown.\n
> Conditional consequence: a source-supported connection between insufficient oil and inadequate lubrication may be explained if the extra conditions are made explicit. Visible oil alone does not establish inadequate lubrication.\n
> Missing: engine architecture, fluid identity, leak origin/rate, quantity trend and reported pressure/temperature indications.

This example deliberately contains no maintenance recommendation and no numerical forecast. Before showing a specific oil-mechanism statement in production, retrieve and verify the actual supporting chapter passage.

## Implementation fit with the current repository

The versioned system prompt already has an explicit HYPOTHESIS boundary. maintenance/contracts.py defines HypothesisDraft fields for possible_explanations, basis, assumptions, information_needed, what_would_weaken_this, limits, and historical_claims. Reuse that intent.

However, generic free-text lists do not currently provide typed technical-reference support for each mechanism/consequence link. Coordinate a shared-schema revision for technical passage supports, hypothesis items and reviewed component mappings with P1 rather than stuffing manual quotes into log-span fields. HypothesisEnvelope must remain parent/run/state-bound and visibly unverified.

Likely server tools to agree (proposals, not implemented):

- search_reference_passages: constrained query, system tags and server-built configuration/access filters.
- get_reference_passages: immutable IDs, original text and metadata.
- get_component_context: reviewed component explanations/mappings with applicability, already represented conceptually in shared contracts.

Never let tool arguments supply arbitrary SQL, file paths, external URLs, owner identity or an authoritative aircraft applicability verdict. The original raw logs remain source evidence; references, user uploads and model summaries remain separately typed.

## Minimal hackathon scope

1. Curate only the relevant FAA handbook sections for lubrication, flight controls and basic airframe structure; no whole-web ingestion.
2. Define a few reviewed mechanism/consequence cards with passage refs and applicability conditions. Manual curation can be more dependable than an autonomous graph-building pipeline at this stage.
3. Retrieve those cards/passages plus real log evidence on an explicit user action.
4. Display up to three source-grounded candidates and material gaps. Return 'not enough information' if no applicable passage supports a useful explanation.
5. Measure this before adding more sources or free-form speculation. No fine-tuning or general knowledge graph is required for the first slice. RAG/structured output is a design choice, not a correctness guarantee.

Keep AD/SAIB/SDR/NTSB integration as optional supplementary sources after the first slice, with their status labels intact. If a manufacturer/model is confirmed and the team has authorized documentation access, then add that documentation with effectivity filters.

## Evaluation before enabling the feature

Freeze test cases for unknown aircraft model, piston/turbine confusion, engine-versus-cylinder numbering, negated leaks, absent measurements, source injection, incompatible manuals, missing or stale revisions, conflicting findings, and inability to retrieve. Test whether:

- The answer's factual/mechanism claims are semantically supported, not just accompanied by valid quotes.
- Assumptions are visible and do not become verified board entries.
- Consequence conditions remain explicit; no unjustified probabilities or deadlines are introduced.
- Missing references cause narrowing/refusal rather than uncited model-memory completion.
- Preliminary/incident reports are not promoted to confirmed causes, and unrelated catastrophes do not dominate ordinary symptom explanations.
- A UI highlight never asserts a precise failed internal component without adequate mapping evidence.

Ask for human aviation-domain review of the curated mechanisms and a sample of released hypotheses. Model fluency and a second model's agreement are not acceptance evidence by themselves.

## Research limitations

This research inspected public official catalogs, access guidance, source descriptions and relevant existing local contracts/prompt. It did not authenticate to OEM portals, verify redistribution rights for any restricted manual, ingest the complete current handbooks, implement the proposed tools, or evaluate a live model. Full current Powerplant PDF fetching was blocked by browser size limits; Boeing portal access returned 403. Recommendations about retrieval budgets, schema and architecture are proposed engineering choices, not claims made by the source publishers.
