# Langfuse telemetry

The application uses Langfuse Python SDK 4.18.0 (OpenTelemetry). The optional exporter is disabled by default. The configured Tokyo project is an external dashboard; no local Langfuse/Postgres/ClickHouse stack is required.

## Private setup and local run

Keep the supplied public/secret keys in ignored `.env.langfuse` with permissions 0600. Set LANGFUSE_ENABLED=true, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL=https://jp.cloud.langfuse.com, LANGFUSE_PROJECT_ID and LANGFUSE_ENVIRONMENT=local. Never put keys into browser source or commit them. The application does not automatically load that private file: explicitly forward it with the overlay.

```sh
docker compose --env-file .env --env-file .env.langfuse -f compose.yaml -f compose.langfuse.yaml config --quiet
docker compose --env-file .env --env-file .env.langfuse -f compose.yaml -f compose.langfuse.yaml build api
docker compose --env-file .env --env-file .env.langfuse -f compose.yaml -f compose.langfuse.yaml up -d --no-build api
```

This preserves the current local DB/provider configuration. For a separately configured managed database, insert the existing Supabase env/Compose override before the Langfuse overlay. Do not accidentally replace the live provider key with a stale blank profile.

## What to open

- Product: http://localhost:8000/maintenance/ — Telemetry link opens the project; each new investigation receives a View Langfuse trace link in its activity.
- Retrieval testing: http://localhost:8000/retrieval-lab — each search receives a link to its own trace beside Pipeline Latency.
- In Langfuse, open a root observation to inspect the execution tree/waterfall. Sessions group runs using their real session UUID. Generations show actual returned model and token usage; automatic costs depend on Langfuse recognizing/configuring that model's prices. No costs or quality/confidence scores are invented.

## Trace tree

```text
agent.run (run_id/session_id/mode/domain; deterministic run-to-trace ID)
  tool.search_records
    retrieval.search
      retrieval.embedding (cache-hit metadata)
      retrieval.recall_and_fusion (worker-thread parent context retained)
        retrieval.bm25_raw
        retrieval.bm25_normalized
        retrieval.dense_cosine
        retrieval.fusion
      retrieval.rerank (executed/skipped/unavailable/busy/error/timeout)
  tool.get_records
  llm.request
    llm.generation (one per provider attempt; real model and usage)
  optional additional tool/generation observations
  validation.draft / validation.answer
  persistence.evidence
  persistence.answer_and_state
```

A direct search starts at retrieval.search. Action requests start at api.action and include nested provider/tool calls when those occur. Validation spans explicitly cover claim/source-span checks, not independent verification of every free-form synthesis or educational statement. Retrieval's existing stage timing/count metadata also accompanies the retrieval span; these numbers are not fabricated retroactive span start/end times.

## Privacy and failure behavior

Metadata-only: identifiers, counts, stage timings, actual model usage and status. No raw questions/prompts/log fields, uploaded documents, provider messages, cookies, DSNs or secret keys are sent by these hooks. Exceptions are represented by type/status only; SDK contexts are exited without exception objects to prevent automatic stack/message capture. Only Langfuse-created instrumentation scopes are exported. Traces stay private; no public-share action is enabled.

The dashboard public project URL and trace ID are safe to expose; credentials are server-only. SDK export is asynchronous/batched, never flushed on each request. Missing credentials/SDK initialization failure leave the app operational. Shutdown has a bounded wait. Capabilities reports enabled/disabled/missing_credentials/initialization_failed; enabled means locally configured, not a remote delivery health guarantee. Verify delivery separately in the dashboard/API.

## Focused verification

`tests/telemetry/test_langfuse.py` checks disabled/exporter-failure behavior, metadata filtering, real SDK async/thread parentage, run/session correlation, generation usage and no raw exception capture using an in-memory exporter (no cloud calls). Existing lab tests verify search behavior is retained. The workflow test requiring a separately configured database may skip when that profile is absent.

Official SDK reference: https://python.reference.langfuse.com/langfuse
Official observability docs: https://langfuse.com/docs/observability/sdk/overview
