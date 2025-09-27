"""
Test health check endpoints.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Momentum backend is running"}


@pytest.mark.api
def test_health_check_response_headers(client: TestClient):
    """Test health check response headers."""
    response = client.get("/")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]