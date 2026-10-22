# Atlas UI overhaul — 22 October 2026

Saved in the Desktop NexaI project; frontend-only work, no Supabase changes.

Design: fixed deep-teal sidebar, cool neutral canvas, green primary actions, coral issue highlights, amber and lavender category accents. The main path is describe → review cases → explore details. All tools are available through the sidebar, with a feature directory explaining contextual actions. Report upload and advanced options remain available without crowding the starting flow.

Demo: eight explicitly invented DEMO-prefixed records; oil, wing fuel leak, and cockpit display examples. New demo storage key avoids mixing earlier fixture sessions with these IDs. Live mode still requires its API and never silently switches to demo data. Oil-loss progression remains opt-in and educational.

Verification: JavaScript syntax checks for all changed modules, diff whitespace check; browser desktop (1440 px) and mobile (390 px); oil sample released two relevant cases with citations; original-source modal, feature directory (10 entries), settings preferences entry checked; no console errors in the tested flow. Phone layout had no horizontal overflow. Existing API client and evidence renderer contracts preserved.

Preview: http://localhost:8765/?demo=1
