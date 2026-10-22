from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from maintenance.config import Settings
from maintenance.features.visuals import VisualService
from maintenance.ingest.aviation import parse_aviation
from maintenance.ingest.facility import parse_facility
from maintenance.retrieval.engine import RetrievalEngine
from maintenance.tools import RunDeps, tool_search_records


class FixtureEncoder:
    model_id = "BAAI/bge-small-en-v1.5"
    revision = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
    dimension = 3
    query_prefix = ""

    def encode_queries(self, texts):
        return np.array([[1.0, 0.0, 0.0] for _ in texts], dtype=np.float32)


def make_test_fixture():
    aviation_csv = (
        b"IDENT,PROBLEM,ACTION\n"
        b"1,CYL #2 INTAKE LEAK,REPL GSKT\n"
        b"2,CYL #2 INTAKE LEAK,REPL GSKT\n"
        b"3,CYL #4 BAFFLE CRACK,WELDED\n"
        b"4,BATTERY FLAT,CHARGED\n"
    )
    facility_csv = (
        b"WORK_ID,SITE_ID,DATE_REQUESTED,PROB_TYPE,DATE_COMPLETED,DESCRIPTION\n"
        b"101,BLDG-A,01/01/23,HVAC,01/02/23,AIR HANDLER MOTOR OVERHEATING\n"
        b"102,BLDG-B,01/03/23,PLUMB,01/04/23,WATER LEAK UNDER SINK\n"
    )
    c_av = parse_aviation(aviation_csv)
    c_fac = parse_facility(facility_csv)

    vectors = {
        str(c_av.manifest.corpus_id): np.array(
            [[1, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32
        ),
        f"{c_av.manifest.corpus_id}:problem_action": np.array(
            [[1, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32
        ),
        str(c_fac.manifest.corpus_id): np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float32),
        f"{c_fac.manifest.corpus_id}:problem_action": np.array(
            [[1, 0, 0], [0, 1, 0]], dtype=np.float32
        ),
    }

    engine = RetrievalEngine([c_av, c_fac], vectors, FixtureEncoder(), reranker=None)
    settings = Settings(
        app_env="test",
        session_signing_secret="s" * 40,
        app_origin="http://localhost:8000",
        _env_file=None,
    )
    app = create_app(settings, engine)
    return TestClient(app), engine, c_av, c_fac, settings


def test_search_endpoint_and_agent_tool_parity():
    client, engine, c_av, c_fac, settings = make_test_fixture()
    with client:
        # 1. Search via POST /search
        req_body = {
            "query_raw": "intake leak",
            "domain": "aviation",
            "top_k": 3,
        }
        res = client.post(
            "/api/maintenance/v1/search",
            json=req_body,
            headers={"origin": settings.app_origin},
        )
        assert res.status_code == 200, res.text
        api_data = res.json()

        # 2. Search via agent tool tool_search_records
        owner_id = uuid4()
        deps = RunDeps(
            owner_id=owner_id,
            session_id=uuid4(),
            run_id=uuid4(),
            mode="EVIDENCE",
            state_revision=1,
            corpus_ids=[c_av.manifest.corpus_id, c_fac.manifest.corpus_id],
            search_engine=engine,
            record_service=engine,
            comparison_service=None,
            pattern_service=None,
            visual_service=VisualService([]),
            fetched_evidence={},
            computed_receipts={},
            tool_events=[],
        )
        import asyncio

        tool_result = asyncio.run(tool_search_records(deps, query="intake leak", domain="aviation", top_k=3))

        # Check parity: same hit count, same record_ids in same order, same scores
        assert len(api_data["hits"]) == tool_result["hit_count"]
        api_rids = [h["record_id"] for h in api_data["hits"]]
        tool_rids = [h["record_id"] for h in tool_result["hits"]]
        assert api_rids == tool_rids
        for api_h, tool_h in zip(api_data["hits"], tool_result["hits"], strict=True):
            assert api_h["record_id"] == tool_h["record_id"]
            assert pytest.approx(api_h["rrf_score"], abs=1e-4) == tool_h["score"]
            assert api_h["compatibility"]["tier"] == tool_h["compatibility"]


def test_trace_truthful_timings_counts_and_degradation():
    client, engine, c_av, c_fac, settings = make_test_fixture()
    with client:
        req_body = {
            "query_raw": "CYL #2 intake leak",
            "domain": "aviation",
            "top_k": 2,
            "quality_mode": True,  # Triggers reranker degradation check
        }
        res = client.post(
            "/api/maintenance/v1/search",
            json=req_body,
            headers={"origin": settings.app_origin},
        )
        assert res.status_code == 200
        data = res.json()

        assert "reranker_unavailable" in data["degraded_branches"]
        assert "trace" in data and data["trace"] is not None
        trace = data["trace"]

        # Check all required stages
        stage_names = [s["stage"] for s in trace["stages"]]
        expected_stages = [
            "queue",
            "normalization",
            "embedding",
            "compatibility_filtering",
            "raw_bm25",
            "normalized_bm25",
            "dense_cosine",
            "fusion",
            "dedup",
            "rerank",
            "top_k_selection",
            "record_fetch",
        ]
        for expected in expected_stages:
            assert expected in stage_names
            assert expected in trace["stage_timings_ms"]
            assert trace["stage_timings_ms"][expected] >= 0.0

        # Truthful counts
        dedup_stage = next(s for s in trace["stages"] if s["stage"] == "dedup")
        assert dedup_stage["count_out"] >= len(data["hits"])  # Dedup pool count before top-k truncation
        topk_stage = next(s for s in trace["stages"] if s["stage"] == "top_k_selection")
        assert topk_stage["count_out"] == len(data["hits"])

        # Query mentions & normalization
        assert trace["original_query"] == "CYL #2 intake leak"
        assert len(trace["normalized_query"]) > 0
        assert len(trace["query_mentions"]) > 0

        # Check hit record snapshot attachment
        hit0 = data["hits"][0]
        assert "record_snapshot" in hit0 and hit0["record_snapshot"] is not None
        assert hit0["record_snapshot"]["record_id"] == hit0["record_id"]
        assert "field_sha256" in hit0["record_snapshot"]
        assert "PROBLEM" in hit0["record_snapshot"]["field_sha256"]


def test_lab_records_pagination_bounds_and_filtering():
    client, engine, c_av, c_fac, settings = make_test_fixture()
    with client:
        # Page 1, page_size 2
        res1 = client.get(
            "/api/maintenance/v1/lab/records",
            params={"domain": "aviation", "page": 1, "page_size": 2},
        )
        assert res1.status_code == 200
        p1 = res1.json()
        assert p1["total"] == 4
        assert p1["total_pages"] == 2
        assert len(p1["items"]) == 2
        assert p1["items"][0]["record_id"] == "aviation:1"
        assert p1["items"][1]["record_id"] == "aviation:2"

        # Page 2
        res2 = client.get(
            "/api/maintenance/v1/lab/records",
            params={"domain": "aviation", "page": 2, "page_size": 2},
        )
        assert res2.status_code == 200
        p2 = res2.json()
        assert len(p2["items"]) == 2
        assert p2["items"][0]["record_id"] == "aviation:3"

        # Search text filter
        res_filter = client.get(
            "/api/maintenance/v1/lab/records",
            params={"search": "baffle"},
        )
        assert res_filter.status_code == 200
        f_data = res_filter.json()
        assert f_data["total"] == 1
        assert f_data["items"][0]["record_id"] == "aviation:3"

        # Invalid corpus UUID must return 404
        fake_uuid = str(uuid4())
        res_404 = client.get(
            "/api/maintenance/v1/lab/records",
            params={"corpus_id": fake_uuid},
        )
        assert res_404.status_code == 404
        assert res_404.json()["error"] == "corpus_not_found"


def test_facility_null_actions_and_real_source_fields():
    client, engine, c_av, c_fac, settings = make_test_fixture()
    with client:
        res = client.get(
            "/api/maintenance/v1/lab/records",
            params={"domain": "facility"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["domain"] == "facility"
            assert item["action_raw"] is None
            assert item["action_normalized"] is None
            assert "WORK_ID" in item["original_fields"]
            assert "SITE_ID" in item["original_fields"]
            assert "DESCRIPTION" in item["original_fields"]
            assert "DESCRIPTION" in item["field_sha256"]
            assert len(item["source_file_sha256"]) == 64


def test_lab_projection_deterministic_provenance_and_max_points():
    client, engine, c_av, c_fac, settings = make_test_fixture()
    with client:
        # First call
        res1 = client.get("/api/maintenance/v1/lab/projection", params={"max_points": 10})
        assert res1.status_code == 200
        p1 = res1.json()

        # Second call must be identical (deterministic)
        res2 = client.get("/api/maintenance/v1/lab/projection", params={"max_points": 10})
        assert res2.status_code == 200
        p2 = res2.json()

        assert p1["method"] == "deterministic_centered_pca2_svd"
        assert p1["label"] == "inspection_only_not_retrieval_score"
        assert len(p1["explained_variance"]) == 2
        assert p1["total_explained_variance"] >= 0.0
        assert p1["model_revision"] == "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
        assert len(p1["source_hash"]) == 64
        assert p1["total_points"] == p2["total_points"] == 6

        # Coordinates identical
        for pt1, pt2 in zip(p1["points"], p2["points"], strict=True):
            assert pt1["record_id"] == pt2["record_id"]
            assert pt1["x"] == pt2["x"]
            assert pt1["y"] == pt2["y"]

        # Slicing max_points bounds output points
        res_bounded = client.get("/api/maintenance/v1/lab/projection", params={"max_points": 3})
        assert res_bounded.status_code == 200
        p_bounded = res_bounded.json()
        assert len(p_bounded["points"]) == 3
        assert p_bounded["corpus_total"] == 6

        # Invalid corpus UUID must return 404
        bad_id = str(uuid4())
        res_bad = client.get("/api/maintenance/v1/lab/projection", params={"corpus_id": bad_id})
        assert res_bad.status_code == 404
        assert res_bad.json()["error"] == "corpus_not_found"


def test_lab_storage_quota_and_source_labels():
    client, engine, c_av, c_fac, settings = make_test_fixture()
    with client:
        res = client.get("/api/maintenance/v1/lab/storage")
        assert res.status_code == 200
        data = res.json()

        assert data["quota_bytes"] == 500000000
        assert data["quota_label"] == "Free plan database quota (configured 500MB)"
        assert data["database_status"] == "unavailable"
        assert data["database_bytes"] is None
        assert "timestamp" in data
        assert "source_labels" in data
        assert data["index_record_count"] == 6
        assert data["index_vector_count"] == 12  # 4 * 2 representations + 2 * 2 representations
        assert data["dense_vector_memory_bytes"] > 0
        assert data["index_counts"]["bm25_indexes"] == 8
        assert data["index_counts"]["dense_matrices"] == 4


def test_storage_null_database_bytes_and_error_handling():
    client, engine, c_av, c_fac, settings = make_test_fixture()

    class FailingPool:
        def acquire(self):
            raise ConnectionError("simulated database failure")

    class FailingDatabase:
        pool = FailingPool()

        async def close(self):
            pass

    orig_db = client.app.state.db
    try:
        with client:
            # Simulate db present but failing during acquisition
            client.app.state.db = FailingDatabase()
            res = client.get("/api/maintenance/v1/lab/storage")
            assert res.status_code == 200
            data = res.json()
            assert data["database_status"] == "error"
            assert data["database_bytes"] is None
            assert data["free_bytes"] is None
            assert data["dense_vector_memory_bytes"] > 0
            assert data["source_labels"]["database"] == "Connected PostgreSQL / pgvector"
    finally:
        client.app.state.db = orig_db


def test_projection_cache_isolation_across_engines():
    # Engine 1
    c1 = parse_aviation(b"IDENT,PROBLEM,ACTION\n1,LEAK,FIXED\n2,CRACK,FIXED\n")
    v1 = {
        str(c1.manifest.corpus_id): np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32),
        f"{c1.manifest.corpus_id}:problem_action": np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32),
    }
    e1 = RetrievalEngine([c1], v1, FixtureEncoder())

    # Engine 2 with completely different vectors
    c2 = parse_aviation(b"IDENT,PROBLEM,ACTION\n1,LEAK,FIXED\n2,CRACK,FIXED\n")
    v2 = {
        str(c2.manifest.corpus_id): np.array([[0.0, 0.0, 5.0], [0.0, 5.0, 0.0]], dtype=np.float32),
        f"{c2.manifest.corpus_id}:problem_action": np.array([[0.0, 0.0, 5.0], [0.0, 5.0, 0.0]], dtype=np.float32),
    }
    e2 = RetrievalEngine([c2], v2, FixtureEncoder())

    settings = Settings(app_env="test", session_signing_secret="s" * 40, _env_file=None)
    cl1 = TestClient(create_app(settings, e1))
    cl2 = TestClient(create_app(settings, e2))

    with cl1:
        res1 = cl1.get("/api/maintenance/v1/lab/projection")
        assert res1.status_code == 200
        pts1 = res1.json()["points"]

    with cl2:
        res2 = cl2.get("/api/maintenance/v1/lab/projection")
        assert res2.status_code == 200
        pts2 = res2.json()["points"]

    # Verify each engine maintains its own distinct cache and coordinates
    assert len(e1._projection_cache) == 1
    assert len(e2._projection_cache) == 1
    assert e1._projection_cache is not e2._projection_cache
    assert pts1 != pts2


def test_canonical_mentions_component_filter():
    client, engine, c_av, c_fac, settings = make_test_fixture()
    with client:
        # CYL #2 in raw problem maps to canonical component 'cylinder'
        res = client.get("/api/maintenance/v1/lab/records", params={"component": "cylinder"})
        assert res.status_code == 200
        data = res.json()
        # Records with cylinder are aviation:1, aviation:2, aviation:3
        assert data["total"] == 3
        for item in data["items"]:
            assert "CYL" in item["problem_raw"]

        # Also verify search engine filter handles component='cylinder'
        search_res = client.post(
            "/api/maintenance/v1/search",
            json={
                "query_raw": "leak",
                "domain": "aviation",
                "filters": {"component": "cylinder"},
            },
            headers={"origin": settings.app_origin},
        )
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert len(search_data["hits"]) > 0
        for hit in search_data["hits"]:
            assert "CYL" in hit["record_snapshot"]["problem_raw"]


def test_auth_and_origin_refusal():
    client, engine, c_av, c_fac, settings = make_test_fixture()
    with client:
        # 1. Invalid owner cookie raises 401 identity_expired
        client.cookies.set("maintenance_owner", "invalid_tampered_cookie_string")
        res_expired = client.get("/api/maintenance/v1/lab/records")
        assert res_expired.status_code == 401
        assert res_expired.json()["error"] == "identity_expired"

        # 2. Mutation to /search without exact origin raises 403 origin_not_allowed
        res_bad_origin = client.post(
            "/api/maintenance/v1/search",
            json={"query_raw": "leak", "domain": "aviation"},
            headers={"origin": "http://evil-attacker.com"},
        )
        assert res_bad_origin.status_code == 403
        assert res_bad_origin.json()["error"] == "origin_not_allowed"
