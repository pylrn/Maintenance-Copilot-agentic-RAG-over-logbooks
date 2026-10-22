"""Workflow integration tests: sessions, actions, uploads, visuals, and SSE replay."""

import asyncio
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from maintenance.config import Settings


@pytest.fixture
def test_app():
    settings = Settings(app_env="test", _env_file=None)
    app = create_app(settings=settings)
    return app


def test_visual_and_component_context_routes(test_app):
    client = TestClient(test_app)

    # 1. Component context
    resp = client.get("/api/maintenance/v1/components/intake_gasket/context")
    assert resp.status_code == 200
    data = resp.json()
    assert data["component_id"] == "intake_gasket"
    assert "Intake" in data["name"]
    assert "node-intake-gasket" in data["asset_mapping_ids"]

    # 2. Visual SVG asset
    svg_resp = client.get("/api/maintenance/v1/visuals/engine_concept_piston_2d")
    assert svg_resp.status_code == 200
    assert "image/svg+xml" in svg_resp.headers["content-type"]


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="isolated PostgreSQL required"
)
@pytest.mark.asyncio
async def test_session_lifecycle_and_actions():
    import httpx
    import numpy as np

    from maintenance.ingest.aviation import parse_aviation
    from maintenance.retrieval.engine import RetrievalEngine

    class MockEncoder:
        model_id = "fixture"
        revision = "fixture"
        dimension = 3
        query_prefix = ""

        def encode_queries(self, texts):
            return np.array([[1, 0, 0] for _ in texts], dtype=np.float32)

    c = parse_aviation(
        b"IDENT,PROBLEM,ACTION\n1,INTAKE LEAK,REPL GSKT\n2,BATTERY FLAT,CHARGED\n3,BAFFLE CRACK,REPAIRED\n"
    )
    mock_engine = RetrievalEngine([c], {str(c.manifest.corpus_id): np.eye(3)}, MockEncoder())

    db_url = os.environ["TEST_DATABASE_URL"]
    settings = Settings(
        app_env="test",
        database_url=db_url,
        session_signing_secret="x" * 40,
        app_origin="http://localhost:8000",
        database_schema="public",
        vector_schema="public",
        _env_file=None,
    )
    app = create_app(settings=settings, search_engine=mock_engine)

    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000"
    ) as client:
        # 1. Check health
        health = await client.get("/api/maintenance/v1/health")
        assert health.status_code == 200
        assert health.json()["workflows_ready"] is True

        # 2. Capabilities
        caps = (await client.get("/api/maintenance/v1/capabilities")).json()
        assert "EVIDENCE" in caps["enabled_modes"]
        assert "HYPOTHESIS" in caps["enabled_modes"]
        assert caps["visuals_available"] is True

        # 3. Create session
        sess_resp = await client.post(
            "/api/maintenance/v1/sessions",
            json={"domain": "aviation", "title": "Test Ingestion Investigation"},
            headers={"Origin": "http://localhost:8000"},
        )
        assert sess_resp.status_code == 200
        sess_data = sess_resp.json()
        session_id = sess_data["session_id"]
        assert sess_data["state_revision"] == 0

        # 4. Patch session
        patch_resp = await client.patch(
            f"/api/maintenance/v1/sessions/{session_id}",
            json={"expected_revision": 0, "title": "Updated Title"},
            headers={"Origin": "http://localhost:8000"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["state_revision"] == 1

        # 5. Stale patch revision should fail with 409
        stale_resp = await client.patch(
            f"/api/maintenance/v1/sessions/{session_id}",
            json={"expected_revision": 0, "title": "Conflicting Update"},
            headers={"Origin": "http://localhost:8000"},
        )
        assert stale_resp.status_code == 409

        # 6. Upload attachment
        up_resp = await client.post(
            f"/api/maintenance/v1/sessions/{session_id}/attachments",
            files={"file": ("pilot_report.txt", b"Pilot reports roughness on ground runup.", "text/plain")},
            headers={"Origin": "http://localhost:8000"},
        )
        assert up_resp.status_code == 200
        assert up_resp.json()["trust_type"] == "user_input"

        # 7. Add user observation
        obs_resp = await client.post(
            f"/api/maintenance/v1/sessions/{session_id}/observations",
            json={"expected_revision": 1, "text": "Pilot reports induction hissing sound on cylinder 2."},
            headers={"Origin": "http://localhost:8000"},
        )
        assert obs_resp.status_code == 200
        assert obs_resp.json()["state_revision"] == 2

        # 8. Post message creating run
        msg_resp = await client.post(
            f"/api/maintenance/v1/sessions/{session_id}/messages",
            json={
                "text": "Cylinder #2 intake is leaking. Similar historical records?",
                "idempotency_key": str(uuid4()),
                "expected_revision": 2,
            },
            headers={"Origin": "http://localhost:8000"},
        )
        assert msg_resp.status_code == 200
        run_data = msg_resp.json()
        assert "run_id" in run_data
        assert run_data["mode"] == "EVIDENCE"
        run_id = run_data["run_id"]

        # Verify model_id in database runs record reflects extractive/v1 when unconfigured
        async with app.state.pool.acquire() as conn:
            run_row = await conn.fetchrow(
                "SELECT model_id, status FROM runs WHERE run_id = $1::uuid",
                run_id,
            )
            assert run_row is not None
            assert run_row["model_id"] == "extractive/v1"

        # Verify cross-owner 404 for run events stream
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as other_client:
            cross_resp = await other_client.get(
                f"/api/maintenance/v1/runs/{run_id}/events",
            )
            assert cross_resp.status_code == 404
            assert cross_resp.json()["error"] == "run_not_found"

        # Verify 404 for non-existent run ID
        fake_run_id = str(uuid4())
        fake_resp = await client.get(
            f"/api/maintenance/v1/runs/{fake_run_id}/events",
        )
        assert fake_resp.status_code == 404
        assert fake_resp.json()["error"] == "run_not_found"

        # Await brief interval to let background runner task settle before lifespan teardown
        await asyncio.sleep(0.2)

        # 9. Handover export
        handover = await client.get(f"/api/maintenance/v1/sessions/{session_id}/handover")
        assert handover.status_code == 200
        assert "# Maintenance Atlas Investigation Handover" in handover.text
