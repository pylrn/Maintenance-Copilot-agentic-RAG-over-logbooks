import numpy as np
from fastapi.testclient import TestClient

from api.main import create_app
from maintenance.config import Settings
from maintenance.ingest.aviation import parse_aviation
from maintenance.retrieval.engine import RetrievalEngine


class Encoder:
    model_id = "fixture"
    revision = "fixture"
    dimension = 3
    query_prefix = ""

    def encode_queries(self, texts):
        return np.array([[1, 0, 0] for _ in texts], dtype=np.float32)


def client():
    c = parse_aviation(
        b"IDENT,PROBLEM,ACTION\n1,INTAKE LEAK,REPL GSKT\n2,BATTERY FLAT,CHARGED\n3,BAFFLE CRACK,REPAIRED\n"
    )
    e = RetrievalEngine([c], {str(c.manifest.corpus_id): np.eye(3)}, Encoder())
    settings = Settings(app_env="test", session_signing_secret="x" * 40, _env_file=None)
    return TestClient(create_app(settings, e)), c


def test_origin_scope_source_lookup_and_no_fake_workflow():
    cl, c = client()
    with cl:
        assert cl.get("/api/maintenance/v1/health").status_code == 200
        body = {"query_raw": "intake leak", "domain": "aviation"}
        assert cl.post("/api/maintenance/v1/search", json=body).status_code == 403
        response = cl.post(
            "/api/maintenance/v1/search", json=body, headers={"origin": "http://localhost:8000"}
        )
        assert response.status_code == 200, response.text
        assert response.json()["hits"][0]["record_id"] == "aviation:1"
        assert "HttpOnly" in response.headers["set-cookie"]
        assert (
            cl.get(
                "/api/maintenance/v1/records/aviation/1",
                params={"corpus_id": str(c.manifest.corpus_id)},
            ).json()["problem_raw"]
            == "INTAKE LEAK"
        )
        assert cl.get("/maintenance").status_code == 503
        assert cl.get("/api/maintenance/v1/capabilities").json()["workflows_ready"] is False
        assert "session_signing_secret" not in cl.get("/api/maintenance/v1/health").text


def test_not_ready_is_service_failure_and_never_empty_search():
    settings = Settings(app_env="test", session_signing_secret="x" * 40, _env_file=None)
    with TestClient(create_app(settings)) as cl:
        response = cl.post(
            "/api/maintenance/v1/search",
            json={"query_raw": "leak", "domain": "aviation"},
            headers={"origin": settings.app_origin},
        )
        assert response.status_code == 503
        assert response.json()["error"] == "retrieval_unavailable"


def test_backend_failure_returns_typed_service_error():
    cl, _ = client()
    with cl:

        async def fail(*args):
            raise TimeoutError("provider detail must not be exposed")

        cl.app.state.search_engine.search = fail
        response = cl.post(
            "/api/maintenance/v1/search",
            json={"query_raw": "leak", "domain": "aviation"},
            headers={"origin": "http://localhost:8000"},
        )
        assert response.status_code == 503
        assert response.json()["error"] == "retrieval_unavailable"
        assert "provider detail" not in response.text


def test_health_on_database_loss_returns_redacted_not_ready():
    cl, _ = client()

    class FailedDatabase:
        async def ready(self):
            raise ConnectionError("sensitive connection details")

        async def close(self):
            pass

    with cl:
        cl.app.state.db = FailedDatabase()
        response = cl.get("/api/maintenance/v1/health")
        assert response.status_code == 503
        assert response.json()["database_ready"] is False
        assert "sensitive" not in response.text
