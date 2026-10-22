"""Tests for contract hardening: corpus_version alias, event replay termination, cancellation sequence, and pins."""

import json
from datetime import datetime, timezone
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from maintenance.config import Settings
from maintenance.events import EventBus
from maintenance.ingest.aviation import parse_aviation
from maintenance.retrieval.engine import RetrievalEngine


class MockEncoder:
    model_id = "fixture"
    revision = "fixture"
    dimension = 3
    query_prefix = ""

    def encode_queries(self, texts):
        return np.array([[1, 0, 0] for _ in texts], dtype=np.float32)


def test_record_fetch_accepts_corpus_version_alias():
    c = parse_aviation(
        b"IDENT,PROBLEM,ACTION\n1,INTAKE LEAK,REPL GSKT\n2,BATTERY FLAT,CHARGED\n"
    )
    e = RetrievalEngine([c], {str(c.manifest.corpus_id): np.eye(2, 3)}, MockEncoder())
    settings = Settings(app_env="test", session_signing_secret="x" * 40, _env_file=None)
    app = create_app(settings, e)
    client = TestClient(app)

    with client:
        # First query search to obtain valid origin and session cookie
        search_resp = client.post(
            "/api/maintenance/v1/search",
            json={"query_raw": "intake leak", "domain": "aviation"},
            headers={"origin": "http://localhost:8000"},
        )
        assert search_resp.status_code == 200

        # Query using corpus_id (standard)
        resp1 = client.get(
            "/api/maintenance/v1/records/aviation/1",
            params={"corpus_id": str(c.manifest.corpus_id)},
        )
        assert resp1.status_code == 200
        assert resp1.json()["problem_raw"] == "INTAKE LEAK"

        # Query using corpus_version alias (as sent by person-2 api-client.mjs)
        resp2 = client.get(
            "/api/maintenance/v1/records/aviation/1",
            params={"corpus_version": str(c.manifest.corpus_id)},
        )
        assert resp2.status_code == 200
        assert resp2.json()["problem_raw"] == "INTAKE LEAK"

        # Neither provided should return 422
        resp3 = client.get("/api/maintenance/v1/records/aviation/1")
        assert resp3.status_code == 422


@pytest.mark.asyncio
async def test_event_replay_terminal_from_db():
    """EventBus.subscribe must exit immediately if a terminal event is replayed from DB."""
    class MockConn:
        async def fetch(self, query, *args):
            return [
                {
                    "sequence": 1,
                    "event_type": "run_started",
                    "public_payload": {"mode": "EVIDENCE"},
                    "created_at": datetime.now(timezone.utc),
                },
                {
                    "sequence": 2,
                    "event_type": "done",
                    "public_payload": {"completed": True},
                    "created_at": datetime.now(timezone.utc),
                },
            ]

    class MockPool:
        def acquire(self):
            class AcquireContext:
                async def __aenter__(self_ctx):
                    return MockConn()

                async def __aexit__(self_ctx, *args):
                    pass

            return AcquireContext()

    bus = EventBus(db_pool=MockPool())
    run_id = uuid4()
    events = []
    # If terminal event returns immediately, this loop will finish on its own without timing out
    async for frame in bus.subscribe(run_id, after_sequence=0):
        for line in frame.split("\n"):
            if line.startswith("data: "):
                payload = json.loads(line[6:].strip())
                events.append(payload["type"])

    assert events == ["run_started", "done"]


@pytest.mark.asyncio
async def test_get_next_sequence_contiguous():
    """EventBus.get_next_sequence must return max(sequence) + 1."""
    class MockConn:
        async def fetchrow(self, query, *args):
            return {"next_seq": 6}

    class MockPool:
        def acquire(self):
            class AcquireContext:
                async def __aenter__(self_ctx):
                    return MockConn()

                async def __aexit__(self_ctx, *args):
                    pass

            return AcquireContext()

    bus = EventBus(db_pool=MockPool())
    run_id = uuid4()
    seq = await bus.get_next_sequence(run_id)
    assert seq == 6


def test_pins_list_route():
    c = parse_aviation(
        b"IDENT,PROBLEM,ACTION\n1,INTAKE LEAK,REPL GSKT\n"
    )
    e = RetrievalEngine([c], {str(c.manifest.corpus_id): np.eye(1, 3)}, MockEncoder())
    settings = Settings(app_env="test", session_signing_secret="x" * 40, _env_file=None)
    app = create_app(settings, e)
    client = TestClient(app)

    with client:
        # Obtain auth cookie via search
        client.post(
            "/api/maintenance/v1/search",
            json={"query_raw": "intake leak", "domain": "aviation"},
            headers={"origin": "http://localhost:8000"},
        )
        # Query pins when workflows not connected -> 503
        fake_session = uuid4()
        resp = client.get(f"/api/maintenance/v1/sessions/{fake_session}/pins")
        assert resp.status_code == 503

        # Mock repo and pool to test 404
        class MockRepo:
            async def get_session(self, sid, oid):
                return None

        class MockPool:
            pass

        app.state.session_repo = MockRepo()
        app.state.pool = MockPool()
        resp_404 = client.get(f"/api/maintenance/v1/sessions/{fake_session}/pins")
        assert resp_404.status_code == 404
