# Investigation flow refinement — 22 October 2026

- Removed sample-case cards, duplicate issue form, step strip, and marketing coverage strip.
- One textarea now starts an investigation and accepts follow-ups; results use the existing answer renderer. No answer-format or backend integration changes.
- Selected query context follows aircraft navigation into internal diagrams. Only regions associated with the reported component get a scenario. Oil-leak source zones remain candidates, not diagnosed failures. Unrelated components remain unmarked.
- Added compact explanation and explicitly expanded conditional complications panel. Oil, fuel leak, structural crack and display-interruption scenarios keep unknowns explicit. FAA educational links accompany physical progression scenarios; display symptoms do not imply further damage.
- Added rotating engine-fan blades, gently pulsing exterior/interior fault highlights and a short drill-down entrance transition. CSS stops these animations with prefers-reduced-motion.
- Restoring or starting a session refreshes the query highlights. Editing context also refreshes an open drill-down.

Checks: five Node assertions for scenario selection (oil, negation, unrelated component, empty context, wing fuel); JavaScript syntax; no duplicate HTML IDs; browser unified submission and two oil demo results; four candidate internal oil zones, no zones/issue box on the other engine, wing-specific explanation; computed rotor/glow animation styles; no browser console errors. Reduced-motion override reviewed in CSS.

Preview screenshot: previews/internal-issue.png. All changes saved in the Desktop NexaI checkout.
