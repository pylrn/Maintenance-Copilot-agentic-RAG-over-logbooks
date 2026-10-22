"""Tests for UI assets, static endpoints, and visual files."""

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from maintenance.config import Settings

ROOT = Path(__file__).resolve().parents[2]


def test_maintenance_page_and_assets_served():
    settings = Settings(app_env="test")
    app = create_app(settings=settings)
    app.state.workflows_ready = True
    client = TestClient(app)

    # Check /maintenance and /maintenance/ serve new Atlas HTML
    resp = client.get("/maintenance")
    assert resp.status_code == 200
    assert "Maintenance Atlas" in resp.text
    assert "atlas-workspace.css" in resp.text

    resp_slash = client.get("/maintenance/")
    assert resp_slash.status_code == 200
    assert "Maintenance Atlas" in resp_slash.text

    # Check static modular CSS
    css_resp = client.get("/static/maintenance/atlas-workspace.css")
    assert css_resp.status_code == 200
    assert "--teal-950" in css_resp.text or "atlas" in css_resp.text

    # Check static ES module
    js_resp = client.get("/static/maintenance/airframe-mapping.mjs")
    assert js_resp.status_code == 200
    assert "detectAirframeSegments" in js_resp.text

    # Check SVG schematic remains accessible
    svg_resp = client.get("/static/assets/engine-concept.svg")
    assert svg_resp.status_code == 200
    assert "engine-concept-svg" in svg_resp.text
    assert "data-component-id" in svg_resp.text


def test_retrieval_lab_page_and_assets_served():
    settings = Settings(app_env="test")
    app = create_app(settings=settings)
    client = TestClient(app)

    # Check /retrieval-lab serves HTML
    resp = client.get("/retrieval-lab")
    assert resp.status_code == 200
    assert "Retrieval Lab" in resp.text
    assert "retrieval_lab.js" in resp.text

    # Check static CSS
    css_resp = client.get("/static/retrieval_lab.css")
    assert css_resp.status_code == 200
    assert "--accent-blue" in css_resp.text

    # Check static JS
    js_resp = client.get("/static/retrieval_lab.js")
    assert js_resp.status_code == 200
    assert "compute_deterministic_pca2" not in js_resp.text  # Frontend renders, backend computes PCA
    assert "executeSearch" in js_resp.text
