"""Optional Langfuse tracing. Metadata only, bounded export, no request-time flush."""

from __future__ import annotations

import asyncio
import functools
import hashlib
import inspect
import json
import logging
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("maintenance.telemetry")
_client = None
_settings = None
_state = "disabled"
# Deliberately excludes query, prompt, raw text, provider messages, secrets and exception text.
_ALLOWED = {
    "run_id",
    "session_id",
    "search_id",
    "domain",
    "mode",
    "model",
    "requested_model",
    "prompt_version",
    "reasoning_effort",
    "fallback_reason",
    "decision",
    "latency_ms",
    "effective_model",
    "provider",
    "status",
    "error_type",
    "record_count",
    "hit_count",
    "claim_count",
    "evidence_count",
    "valid",
    "fallback",
    "degraded_branches",
    "pipeline_version",
    "stage_timings_ms",
    "stage_counts",
    "embedding_cache_hit",
    "record_ids",
    "corpus_ids",
    "dimensions",
    "input_characters",
    "output_characters",
    "tool_name",
    "tool_call_count",
    "tool_call_id",
    "usage",
    "validation_scope",
    "state_revision",
    "elapsed_ms",
    "stage",
    "quality_mode",
    "intent",
    "type",
}


def safe_metadata(fields: dict[str, Any]) -> dict[str, Any]:
    def bounded(value):
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            # Metadata identifiers/enums only; reject secret/DSN-shaped values even in allowed keys.
            if any(
                x in value.lower()
                for x in ["sk-", "pk-lf-", "://", "bearer ", "password", "secret="]
            ):
                return "[redacted]"
            return value[:160]
        if isinstance(value, (list, tuple)):
            return [bounded(v) for v in value[:50]]
        if isinstance(value, dict):
            return {str(k)[:64]: bounded(v) for k, v in list(value.items())[:40]}
        return str(value)[:80] if type(value).__module__ == "uuid" else None

    return {k: bounded(v) for k, v in fields.items() if k in _ALLOWED}


def configure(settings):
    global _client, _settings, _state
    _settings = settings
    _client = None
    _state = "disabled"
    if not settings.langfuse_enabled:
        return
    secret = getattr(settings, "langfuse_secret_key", None)
    public = getattr(settings, "langfuse_public_key", "")
    if not secret or not public:
        _state = "missing_credentials"
        return
    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=public,
            secret_key=secret.get_secret_value(),
            base_url=settings.langfuse_base_url,
            environment=settings.langfuse_environment,
            timeout=3,
            flush_at=32,
            flush_interval=2,
            # Avoid exporting unrelated framework instrumentation (SQL, HTTP headers etc.).
            should_export_span=lambda span: span.instrumentation_scope.name == "langfuse-sdk",
        )
        _state = "enabled"
    except Exception as exc:
        _state = "initialization_failed"
        logger.warning("Telemetry initialization failed: %s", type(exc).__name__)


def trace_id_for_run(run_id) -> str:
    # Same deterministic mapping as SDK create_trace_id(seed=...). No network call.
    return hashlib.sha256(str(run_id).encode()).hexdigest()[:32]


def trace_info(trace_id=None, run_id=None):
    if _client is None:
        return {}
    if run_id is not None:
        trace_id = trace_id_for_run(run_id)
    if trace_id is None:
        try:
            trace_id = _client.get_current_trace_id()
        except Exception:
            return {}
    if not trace_id:
        return {}
    project = getattr(_settings, "langfuse_project_id", "")
    base = _settings.langfuse_base_url.rstrip("/")
    result = {"trace_id": trace_id}
    if project and project.isalnum() and len(trace_id) == 32:
        result["trace_url"] = f"{base}/project/{project}/traces/{trace_id}"
    return result


def status():
    project = getattr(_settings, "langfuse_project_id", "")
    return {
        "enabled": _client is not None,
        "state": _state,
        "content_capture": False,
        "dashboard_url": f"{_settings.langfuse_base_url.rstrip('/')}/project/{project}/traces"
        if _client is not None and project and project.isalnum()
        else None,
    }


class Observation:
    def __init__(self, span=None):
        self.span = span

    def update(self, *, metadata=None, model=None, usage=None, level=None):
        if self.span is None:
            return
        try:
            fields = {"metadata": safe_metadata(metadata or {})}
            if model:
                fields["model"] = model
            if usage:
                # Values come from the provider response, never estimated.
                fields["usage_details"] = {
                    k: int(v)
                    for k, v in usage.items()
                    if k in {"input", "output", "total"} and isinstance(v, int) and v >= 0
                }
            if level:
                fields["level"] = level
            self.span.update(**fields)
        except Exception:
            pass


@contextmanager
def observation(name, kind="span", **metadata):
    """Never suppress app exceptions or let SDK failures replace them.

    Exit SDK context with no exception so OTel cannot serialize raw exception text/stack.
    """
    cm = propagation = None
    active = Observation()
    if _client is not None:
        try:
            options = {"name": name, "as_type": kind, "metadata": safe_metadata(metadata)}
            if name == "agent.run" and metadata.get("run_id"):
                options["trace_context"] = {"trace_id": trace_id_for_run(metadata["run_id"])}
            if metadata.get("session_id"):
                from langfuse import propagate_attributes

                propagation = propagate_attributes(
                    session_id=str(metadata["session_id"]), trace_name=name
                )
                propagation.__enter__()
            cm = _client.start_as_current_observation(**options)
            active = Observation(cm.__enter__())
        except Exception:
            if cm:
                try:
                    cm.__exit__(None, None, None)
                except Exception:
                    pass
            cm = propagation = None
    try:
        yield active
    except BaseException as exc:
        active.update(
            metadata={
                "status": "cancelled" if isinstance(exc, asyncio.CancelledError) else "error",
                "error_type": type(exc).__name__,
            },
            level="ERROR",
        )
        raise
    finally:
        if cm:
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass
        if propagation:
            try:
                propagation.__exit__(None, None, None)
            except Exception:
                pass


def observed(name, kind="span", metadata=None, result_metadata=None):
    """Decorator capturing selected counters/identifiers, never function arguments/results."""

    def decorate(fn):
        def begin(args, kwargs):
            try:
                return metadata(*args, **kwargs) if metadata else {}
            except Exception:
                return {}

        def finish(span, result):
            if result_metadata:
                try:
                    span.update(metadata=result_metadata(result))
                except Exception:
                    pass

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapped(*args, **kwargs):
                with observation(name, kind, **begin(args, kwargs)) as span:
                    result = await fn(*args, **kwargs)
                    finish(span, result)
                    return result

            return async_wrapped

        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            with observation(name, kind, **begin(args, kwargs)) as span:
                result = fn(*args, **kwargs)
                finish(span, result)
                return result

        return wrapped

    return decorate


async def shutdown():
    global _client
    client, _client = _client, None
    if client:
        try:
            await asyncio.wait_for(asyncio.to_thread(client.shutdown), timeout=4)
        except Exception:
            logger.warning("Telemetry shutdown did not complete within deadline")


def log_stage(**fields):
    logger.info(json.dumps(safe_metadata(fields), default=str))
