# Component explorer UI — 22 October 2026

Implemented in the Desktop NexaI checkout on person-2-agent-experience.

- Replaced fixed diagnostic reports with authored SVG component schematics and selectable numbered regions: engine lubrication circuit, wing structure, avionics interfaces, generic structure.
- Engine oil-loss exploration is an explicit, separate unverified educational scenario. It offers possible source areas and four conditional stages, without predicted timelines, probability, or log-derived diagnosis.
- Educational basis: FAA Aviation Maintenance Technician Handbook—Powerplant, Volume 2, lubrication systems: https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-32-AMT-Powerplant-Vol-2.pdf
- The engine outline illustrates a turbine-style arrangement, not the unknown aircraft configuration of a MaintNet record. No geometry/model applicability is asserted.
- Removed fabricated crack stations, seal failures, ultrasonic readings and nominal telemetry from drill-downs. Unknown query mappings no longer select the right engine by default. Ambiguous engine mentions highlight both sides; cylinder numbers do not select engine side.
- Keyboard interaction, pressed states, text-safe context rendering and narrow-screen stacking included. No Supabase/platform files changed.

Verification: node --check on both modules; git diff --check; browser demo initialization, Engine1 query mapping, keyboard engine/wing navigation, wing subregion selection, oil-loss expansion and stage selection; browser console showed no errors. Narrow preview at approximately 700 px rendered stacked controls. Database/live agent integration remains separate work.

Preview: python -m http.server 8765 --bind 127.0.0.1 --directory api/static/maintenance
Open http://localhost:8765/?demo=1 and select Engine 1, then Explore oil-loss progression.
