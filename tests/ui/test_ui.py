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

    # Check /maintenance serves HTML
    resp = client.get("/maintenance")
    assert resp.status_code == 200
    assert "MAINTENANCE" in resp.text
    assert "Aviation Maintenance Copilot" in resp.text

    # Check static CSS
    css_resp = client.get("/static/maintenance.css")
    assert css_resp.status_code == 200
    assert "--navy-950" in css_resp.text

    # Check static JS
    js_resp = client.get("/static/maintenance.js")
    assert js_resp.status_code == 200
    assert "initNewSession" in js_resp.text

    # Check SVG schematic
    svg_resp = client.get("/static/assets/engine-concept.svg")
    assert svg_resp.status_code == 200
    assert "engine-concept-svg" in svg_resp.text
    assert "data-component-id" in svg_resp.text
