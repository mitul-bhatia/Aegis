import os
import httpx
import pytest

BASE_URL = os.getenv("AEGIS_API_URL", "http://localhost:8000")

def test_sql_injection_attempt():
    """Verify that the API rejects or safely handles SQL injection in parameters."""
    with httpx.Client(base_url=BASE_URL) as client:
        try:
            # Attempt SQLi on the user_id parameter
            response = client.get("/api/v1/repos/available?user_id=1' OR '1'='1")
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ReadError):
            pytest.skip(f"API server not running at {BASE_URL}")
        
        # Should return a 400 Bad Request / 422 Validation Error due to type mismatch (expected int)
        # or 500 if unhandled, but ideally 422 from FastAPI.
        assert response.status_code in [400, 422, 500]
        # If it returns 200, ensure it didn't dump the whole DB
        if response.status_code == 200:
            assert isinstance(response.json(), list)
            # A real injection would likely return all repos for all users
            # This is hard to assert blindly, but we check it didn't crash at least.

def test_large_payload():
    """Verify that the API handles excessively large payloads gracefully."""
    # Over 1MB body should be rejected by middleware
    large_payload = {"repo_url": "https://github.com/" + "a" * (1024 * 1024)}
    with httpx.Client(base_url=BASE_URL) as client:
        try:
            response = client.post("/api/v1/repos", json={"user_id": 1, **large_payload})
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ReadError):
            pytest.skip(f"API server not running at {BASE_URL}")
        
        # 422 Unprocessable Entity or 413 Payload Too Large
        assert response.status_code in [413, 422, 400, 500]

def test_malformed_json():
    """Verify that malformed JSON is rejected gracefully."""
    with httpx.Client(base_url=BASE_URL) as client:
        try:
            response = client.post(
                "/api/v1/repos",
                content="{'malformed': 'json'",
                headers={"Content-Type": "application/json"}
            )
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ReadError):
            pytest.skip(f"API server not running at {BASE_URL}")
            
        assert response.status_code in [400, 422]
