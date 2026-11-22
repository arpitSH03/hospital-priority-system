"""
Tests for FastAPI static frontend serving.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_index_html_serving():
    """Verify that root '/' serves frontend index.html."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Hospital Emergency Priority System" in response.text
    assert "DSA-Driven Triage" in response.text


def test_static_assets_serving():
    """Verify that style.css and app.js are served correctly."""
    css_resp = client.get("/style.css")
    assert css_resp.status_code == 200
    assert "Triage Priority Colors" in css_resp.text

    js_resp = client.get("/app.js")
    assert js_resp.status_code == 200
    assert "HospitalApp" in js_resp.text
