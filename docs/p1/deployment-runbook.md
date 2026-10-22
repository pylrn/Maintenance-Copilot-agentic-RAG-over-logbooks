# Deployment runbook

The local PostgreSQL and native API are the verified development environment. No public provider/host is configured by this work. Keep the retrieval platform available for P2 integration while leaving unavailable agent/UI capabilities explicit.

## Build and runtime

- Python 3.11; exact resolver lock in `uv.lock`, hashed export in `requirements.lock`.
- Linux uses the explicit official CPU PyTorch index; Mac uses the normal CPU-capable PyPI wheel. Dependencies remain pinned and hashed. Docker installs the same lock with that extra index to find `+cpu` wheels.
- Compose's database is digest-pinned PostgreSQL 17/pgvector. The API Docker base is digest-pinned Python 3.11.12-slim, non-root UID 10001.
- Models/artifacts are not in the image or Git. Compose mounts them read-only. Prepackage those directories or mount trusted persistent object/volume storage on the host. Test read permissions and symbolic links in the Hugging Face cache on the target platform.
- `MODEL_CACHE_DIR` and `ARTIFACT_DIR` must point to the packaged data. `EMBEDDING_REVISION` must match manifest/model pin. Do not silently download or regenerate an index on a request.
- Run migrations and ingestion via the owner/admin CLI, never a public tool/route. Migrations are checksummed, advisory-locked and transactional; do not edit applied files.

## Credentials and access

Set server-only DB DSN/TLS, stable 32+ byte signing secret, DeepSeek key/model/allowlist and HTTPS `APP_ORIGIN`. Give developers separate DBs and keys. The current signed anonymous identity isolates session IDs; it is not organization SSO. Configure access protection/rate limiting before an unrestricted public demo. No health/capabilities endpoint returns credentials or connection strings.

Use a runtime DB role limited to required application tables rather than the local superuser. Give schema/ingest privileges only to the admin process. Preserve immutable corpus/evidence invariants and backups. Private upload storage must be owner-scoped and persistent; P2 must select/test it before enabling uploads in a hosted instance.

## Readiness and release

`GET /api/maintenance/v1/health` reports database/schema/index readiness and P2 workflow status. It is not a guarantee of provider capability. Confirm live tool/structured-draft smoke checks, evidence release and rejection paths, source lookup/versioning, both search channels, TLS/Origin/session isolation, SSE reconnect without rerun, cancellation and restart restore. A new worker must not steal an unexpired run lease. Validate container RAM and cold/warm latency on the selected host; local timings are not hosting promises.

Before release, P2's unsupported questions, human citation review and browser tests must pass. Retain model/corpus/prompt/schema/index versions and actual metric denominators in the release notes. Source licensing/attribution and simulated-observation labels must remain visible. No public deployment URL or submission is claimed until those checks occur.

## Rollback and recovery

Retain the previous image, schema version, model/index manifest and immutable source versions. Do not downgrade the DB by deleting history; restore a tested backup or apply a forward-compatible corrective migration. Atomic artifact manifest replacement avoids partially built vectors; retain the previous referenced NPZ until no process uses it. Reconnects replay persisted run events, not repeated inference. Provider outages must leave previous validated answers readable and report a typed service failure for new work.
