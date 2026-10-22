# Vercel frontend with the local retrieval backend

The deployed UI uses a same-origin `/api/...` reverse proxy through an HTTPS Cloudflare Quick Tunnel to this computer's API on127.0.0.1:8000. Local PostgreSQL/pgvector and models stay on this computer. Gemini/Langfuse/database keys are not copied to Vercel or the frontend bundle.

Primary site: https://maintenance-copilot-dun.vercel.app/maintenance/

Secondary site: https://nexaiimplimentation.vercel.app/maintenance/

The second previously failing project, `nexai_implimentation`, uses the same static configuration and backend connection. Both projects track GitHub `main`.

## Fixed deployment failures

- Explicit `framework: null` prevents Vercel from treating the frontend as a FastAPI function while Python files are excluded.
- Root-anchored `.vercelignore` entries prevent `/maintenance/` from accidentally excluding `public/maintenance/`.
- `scripts/build_vercel.mjs` emits Build Output API v3: static UI, root and `/maintenance/` routes, and an external API proxy.
- All generated root and nested JS modules use the same canonical assets; `.mjs` is served as JavaScript.
- Build-generated deployment config selects live mode when an HTTPS backend exists; `?demo=1` explicitly opens demo mode. Missing backend configuration produces labelled demo mode and503 JSON on API routes.
- Browser mutations retain exact-origin protection: only localhost and the explicitly configured Vercel production domains are accepted. Owner cookies remain HttpOnly/SameSite strict and are Secure on HTTPS. Sessions are persisted locally, not in Vercel static storage.

## Configuration

Vercel environment variable for Production and Preview:

`MAINTENANCE_BACKEND_ORIGIN=https://<current-tunnel-hostname>`

It must be a public HTTPS origin, without credentials, path or query string. Build rejects obvious local addresses and credential-bearing URLs. Only configure a trusted backend; do not put credentials in its URL.

Local `.env.vercel-local` is ignored and contains the tunnel origin and explicit `ADDITIONAL_APP_ORIGINS` JSON. Keep `.env` and `.env.langfuse` private.

Backend start/update:

```sh
docker compose --env-file .env --env-file .env.langfuse --env-file .env.vercel-local \
  -f compose.yaml -f compose.langfuse.yaml -f compose.vercel-local.yaml \
  up -d --no-build api
```

The deployed container includes the Vercel origin/cookie changes. A future ordinary image build must include the current source. No database migrations were required.

## Tunnel lifecycle — development availability

The tunnel is a detached `cloudflared` process. Its PID/log are ignored under `.runtime/`. Reuse or start it with:

```sh
python3 scripts/start_vercel_tunnel.py
```

Cloudflare Quick Tunnels do not provide a fixed hostname or production uptime. This computer, Docker, the API and the tunnel must remain running and network-connected. Sleep, reboot, process termination or network loss can interrupt access. Restarting the tunnel can change its URL; update the Vercel environment variable in **both** projects and redeploy. No automatic daily quota/model retry or public submission is enabled.

This is a working local-backend development connection, not an always-on hosted backend. For a permanent deployment, use a named tunnel with a stable domain/account or deploy the API/database/models to an appropriate always-on service. Do not disable Vercel deployment protection to test preview URLs; use authenticated `vercel curl`.

## Verification

- `/`, `/maintenance/`, JS/CSS assets and `/deployment-status.json`.
- `/api/maintenance/v1/health` and capabilities through the Vercel domain.
- Live POST session/message with the Vercel Origin, persisted owner cookie, SSE completion, reloaded answer and original cited fields.
- Positive and abstention query suite with `extractive/v1`, avoiding model API quota consumption.
- HTTPS cookie Secure/HttpOnly/SameSite, origin rejection, actual deployment mode and linked GitHub main branch.

Browser automation was unavailable in the current Work settings. Deployment checks use real HTTPS requests and static dependency checks; no browser-rendering claim is made.

## Verified deployment — 22 October 2026

Implementation commit: `5d030ae`. Both GitHub-linked Vercel deployments succeeded.

- Primary: https://maintenance-copilot-dun.vercel.app/maintenance/
- Secondary: https://nexaiimplimentation.vercel.app/maintenance/
- Public primary query regression: **10/10 passed**, including evidence, abstention and original source quote/hash checks.
- Both public domains passed asset, health, session-cookie, streaming-completion, supported-answer, insufficient-evidence and rejected-origin checks.
- Local checks: **132 Python tests passed, 1 skipped; 14 JavaScript tests passed**.
- These deployment checks used `extractive/v1`; no model API quota was consumed. They verify the deployment path, not live model performance.

Machine-readable results are in `verification/primary.json`, `verification/secondary.json` and `verification/query-regression.json`. Browser rendering was not checked because local browser automation was disabled. The computer/tunnel availability requirements above still apply.
