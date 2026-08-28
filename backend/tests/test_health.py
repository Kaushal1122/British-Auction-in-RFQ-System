import pytest
from fastapi.testclient import TestClient


def test_health_endpoint_root(client: TestClient):
    """Verify that GET /health returns HTTP 200 and status 'ok'."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


def test_root_endpoint(client: TestClient):
    """Verify that GET / returns HTTP 200 with API metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "status" not in data or data.get("health") == "/health"
    assert "version" in data
