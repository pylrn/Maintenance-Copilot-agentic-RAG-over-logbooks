# Distinct wing cutaways — 22 October 2026

Replaced the single wing template with six per-segment profiles in wing-profiles.mjs:

- Slats: forward surface, support track, wing-nose interface; side-section extension drawing.
- Flaps: panel, drive linkage, track/carriage; illustrated track-guided extension.
- Ailerons: panel, hinge fittings, control connection; hinge-line cutaway.
- Spoilers: raised panel, actuator connection, hinge line; raised-panel illustration.
- Wing box/tank: enclosure, spars/ribs, access covers, feed/vent paths; internal-volume cutaway.
- Winglets: shell, root attachment, reinforcement; upright tip structure.

The red note follows the selected internal part and explicitly leaves its condition unverified. Live source-record detail still requires integration; backend availability alone will not populate this panel. Existing generic engine, avionics and structure views are retained. The spoiler hit area was shifted out from beneath the engine to support direct mouse selection.

Illustrations are authored generic layouts, not aircraft-specific diagrams. Educational reference: FAA Airframe Handbook, https://www.faa.gov/documentlibrary/media/advisory_circular/ac_65-15a.pdf . Hardware configuration and applicability remain unknown.

Verification: six Node regression tests pass, including distinct scenes/part lists, matching hotspot counts and valid scenario indices. Browser checked all six wing profiles; direct mouse spoiler selection; keyboard profile navigation; selected internal part updates the red note; no console errors. JS syntax and whitespace checks pass.
