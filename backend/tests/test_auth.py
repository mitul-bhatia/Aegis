import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_auth.db"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal, init_db
from backend.app.models.entities import User

client = TestClient(app)


def test_auth_me_unauthenticated_returns_401():
    """Unauthenticated GET /api/v1/auth/me must fail closed with 401."""
    init_db()
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_auth_me_with_bearer_returns_user():
    """Bearer token with valid user id returns profile."""
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.github_id == 99999902).first()
        if not user:
            user = User(
                github_id=99999902,
                github_username="auth_unit_test_user",
                github_avatar_url="https://github.com/ghost.png",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {user_id}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["github_username"] == "auth_unit_test_user"
