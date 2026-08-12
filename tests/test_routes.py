import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert data["checks"]["groq_api"] == "configured"
    assert data["checks"]["mistral_api"] == "configured"

def test_unauthenticated_me_endpoint():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

def test_demo_login_endpoint():
    response = client.post("/api/v1/auth/demo")
    assert response.status_code == 200
    data = response.json()
    assert data["github_username"] == "demo-user"
    assert "aegis_session" in response.cookies
