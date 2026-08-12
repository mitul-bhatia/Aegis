import os
import random
import pytest
from database.db import engine, SessionLocal, get_db, Base
from database.models import User, Repo, Scan, ScanStatus, DocumentEmbedding, VulnSignature

def test_database_initialization():
    """Verify tables creation and connection."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        rand_id = random.randint(10000, 999999)
        user = db.query(User).filter(User.github_username == f"testuser_{rand_id}").first()
        if not user:
            user = User(
                github_id=rand_id,
                github_username=f"testuser_{rand_id}",
                github_avatar_url="https://example.com/avatar.png",
                github_token="encrypted_test_token"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        assert user.id is not None

        repo = Repo(
            user_id=user.id,
            full_name=f"testuser_{rand_id}/testrepo",
            is_indexed=True,
            status="monitoring"
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)
        assert repo.id is not None

        scan = Scan(
            repo_id=repo.id,
            commit_sha=f"sha_{rand_id}",
            branch="main",
            status=ScanStatus.QUEUED.value
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        assert scan.id is not None
        assert scan.status == "queued"

    finally:
        db.close()
