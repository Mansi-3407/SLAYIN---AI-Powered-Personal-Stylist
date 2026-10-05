"""API integration tests."""

from fastapi.testclient import TestClient

from src.app import app


def test_health_endpoint():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
