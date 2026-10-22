# Regional cutaways and issue fixtures — 22 October 2026

Added ten distinct non-wing profiles in airframe-profiles.mjs:

| Exterior region | Internal callouts | Invented issue example |
| --- | --- | --- |
| Nose/radome | Shell, antenna mount, attachment ring | Radome crack near the attachment ring |
| Cockpit | Panes, frame/seals, heating connection | Cockpit windshield crack |
| Avionics bay | Racks, power distribution, data connectors | Avionics connector intermittent |
| Forward cabin | Window surrounds, floor supports, sidewall interfaces | Forward cabin window seal leak |
| Aft cabin | Skin/frames, rear pressure boundary, floor interface | Aft cabin pressure leak |
| Center box | Carry-through structure, keel beam, floor attachments | Center wing box crack |
| Tail cone/APU | Enclosure, inlet, exhaust/mounts | APU exhaust vibration in tail cone |
| Horizontal stabilizer | Skin, reinforcement, root fitting | Left horizontal stabilizer crack |
| Elevator | Panel, hinges, input linkage | Right elevator stiff movement |
| Rudder/vertical fin | Rudder surface, hinge attachments, control input | Rudder hinge excessive play |

The main aircraft and wing cutaways remain intact. Both sides of symmetrical surfaces share the relevant assembly profile; the selected exterior name retains side information. Doors, landing gear and pylons still use the existing generic structural fallback.

The red box uses component-specific symptom rules and missing findings. It follows internal selection and labels the part condition as unverified. Possible consequences remain conditional, with no claimed diagnosis, failure probability or timeline. No maintenance procedures or measured telemetry are fabricated.

Added demo-component-cases.mjs with ten invented DEMO-011 through DEMO-020 cases; there are now 18 demo records total. The existing demo storage key is preserved. Synthetic records are marked simulated and use no source hashes. A selected region alone does not manufacture an issue: without report context the cutaway remains neutral. Generic anatomical mentions are not treated as a match for a specific new symptom fixture.

Query mapping now distinguishes forward/aft cabin, tail wings versus main wings, elevator versus stabilizer, vertical fin/rudder and tail cone/APU. Nose-gear queries do not automatically select the radome; APU oil reports do not light the main engines simply because they mention oil.

Verification:
- Ten Node tests pass across the mapping and profile test files; distinct geometry/part lists, valid callout counts, matching region IDs, all ten demo examples and negation/neutral context are checked.
- Browser opened all ten regional cutaways with their issue boxes and unique controls.
- Nose case produced DEMO-011 and rudder case produced DEMO-020; internal selection updates the issue box.
- No console errors in checked flows. At a 390 px phone viewport the page had no horizontal overflow. Reduced-motion styling is inherited.
- JavaScript syntax and git whitespace checks pass.

Educational references: FAA Airframe Handbook (https://www.faa.gov/documentlibrary/media/advisory_circular/ac_65-15a.pdf); FAA Powerplant Handbook Vol. 2 for the illustrative APU compartment (https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-32-AMT-Powerplant-Vol-2.pdf). These authored drawings are not model-specific geometry or source-log evidence.

Saved screenshots: previews/nose-cutaway.png and previews/rudder-cutaway.png. Current integration entry point: ../../INTEGRATION_HANDOVER.md. Live source mapping and canonical API adaptation remain integration tasks.
