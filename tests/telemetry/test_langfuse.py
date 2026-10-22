import asyncio
from types import SimpleNamespace

import pytest

from maintenance import telemetry


@pytest.fixture(autouse=True)
def isolated_telemetry(monkeypatch):
    monkeypatch.setattr(telemetry, "_client", None)
    monkeypatch.setattr(
        telemetry,
        "_settings",
        SimpleNamespace(
            langfuse_project_id="testproject", langfuse_base_url="https://jp.cloud.langfuse.com"
        ),
    )


@pytest.mark.asyncio
async def test_disabled_and_exporter_failure_preserve_business_result(monkeypatch):
    @telemetry.observed("test.operation")
    async def business():
        return 42

    assert await business() == 42

    class BrokenClient:
        def start_as_current_observation(self, **kwargs):
            raise RuntimeError("sensitive-key-must-not-be-logged")

    monkeypatch.setattr(telemetry, "_client", BrokenClient())
    assert await business() == 42
    with pytest.raises(ValueError, match="original business error"):
        with telemetry.observation("test.failure"):
            raise ValueError("original business error")


def test_metadata_allowlist_drops_raw_inputs_and_secret_shaped_values():
    assert telemetry.safe_metadata(
        {
            "query": "private text",
            "prompt": "private prompt",
            "status": "completed",
            "model": "sk-private-credential",
            "record_count": 6,
        }
    ) == {"status": "completed", "model": "[redacted]", "record_count": 6}


@pytest.mark.asyncio
async def test_actual_sdk_async_thread_parentage_and_no_exception_content(monkeypatch):
    pytest.importorskip("langfuse")
    from langfuse import Langfuse
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    client = Langfuse(
        public_key="pk-lf-local-test",
        secret_key="sk-lf-local-test",
        span_exporter=exporter,
        tracer_provider=TracerProvider(),
    )
    monkeypatch.setattr(telemetry, "_client", client)
    sentinel = "PRIVATE_ERROR_CONTENT_MUST_NEVER_BE_EXPORTED"

    @telemetry.observed("test.child", "retriever")
    def child():
        return 7

    with telemetry.observation("agent.run", "agent", run_id="fixed-run", session_id="test-session"):
        assert await asyncio.to_thread(child) == 7
        with pytest.raises(ValueError):
            with telemetry.observation("test.error"):
                raise ValueError(sentinel)
        with telemetry.observation("llm.generation", "generation") as generation:
            generation.update(model="actual-model", usage={"input": 12, "output": 4})
    client.flush()
    spans = {s.name: s for s in exporter.get_finished_spans()}
    assert set(spans) == {"agent.run", "test.child", "test.error", "llm.generation"}
    parent = spans["agent.run"]
    assert format(parent.context.trace_id, "032x") == telemetry.trace_id_for_run("fixed-run")
    for name in ["test.child", "test.error", "llm.generation"]:
        assert spans[name].parent.span_id == parent.context.span_id
        assert spans[name].context.trace_id == parent.context.trace_id
    assert sentinel not in str([(dict(s.attributes), list(s.events)) for s in spans.values()])
    assert not spans["test.error"].events
    assert any("session" in k and v == "test-session" for k, v in parent.attributes.items())
    client.shutdown()
