import os
import httpx
import pytest

# Default to testserver for internal client testing, or a live URL if provided
BASE_URL = os.getenv("AEGIS_API_URL", "http://localhost:8000")

def test_health_check():
    """Verify that the API health check endpoint returns 200 OK."""
    with httpx.Client(base_url=BASE_URL) as client:
        try:
            response = client.get("/health")
        except httpx.ConnectError:
            pytest.skip(f"API server not running at {BASE_URL}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

def test_get_current_user_unauthorized():
    """Verify that accessing protected routes without auth handles correctly (if applicable)."""
    with httpx.Client(base_url=BASE_URL) as client:
        try:
            response = client.get("/api/v1/auth/me")
        except httpx.ConnectError:
            pytest.skip(f"API server not running at {BASE_URL}")
        
        # Unauthenticated requests should fail closed
        assert response.status_code in [401, 403]

def test_list_repos():
    """Verify that the repository list endpoint returns an array."""
    with httpx.Client(base_url=BASE_URL) as client:
        try:
            response = client.get("/api/v1/repos/available?user_id=1")
        except httpx.ConnectError:
            pytest.skip(f"API server not running at {BASE_URL}")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

def test_create_repo_invalid_url():
    """Verify that invalid repository URLs are rejected."""
    with httpx.Client(base_url=BASE_URL) as client:
        try:
            response = client.post("/api/v1/repos", json={"user_id": 1, "repo_url": "not-a-url"})
        except httpx.ConnectError:
            pytest.skip(f"API server not running at {BASE_URL}")
        
        # We expect a validation error
        assert response.status_code in [400, 422, 500]
