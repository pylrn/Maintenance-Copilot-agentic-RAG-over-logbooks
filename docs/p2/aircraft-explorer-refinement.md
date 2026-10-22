# Aircraft explorer refinement — 22 October 2026

- Replaced the 20-region outline with 33 selectable SVG regions. Added dedicated spoilers, ailerons, winglets, elevators, door and landing-gear areas; refined wing shape, engine nacelles, cockpit glazing, cabin windows and body contours.
- Increased the desktop aircraft canvas from 330 to 560 px. Soft metal gradients and shadows replace construction lines and station annotations. Mobile scales to its available width without horizontal overflow.
- Extracted UI-only mention mapping into airframe-mapping.mjs. Named wing controls map to the corresponding region; unspecified side highlights both wings. Left/right, LH/RH, L/H/R/H and port/starboard aliases are accepted. Cylinder numbers do not select engine side.
- Wing-control reports now retain their context in the internal view. Symptom/source mapping remains illustrative and cannot establish an actual damaged part.
- Moved internal part controls into a compact grid and placed the explanation/conditional complications alongside the diagram. Removed the extra full-width context and explanation rows.

Verification: five Node test cases in tests/ui/airframe-mapping.test.mjs (multiple assertions covering mapping, real SVG IDs and internal scenarios); JS syntax checks; unique HTML IDs; browser left flap highlight and mouse navigation into its correct internal control region; both-wing fuel-leak highlighting; compact sidebar explanation; mobile viewport checked at 390 px without overflow; no console errors in the tested flow.

Screenshots: previews/aircraft-explorer.png and previews/compact-wing-detail.png.
