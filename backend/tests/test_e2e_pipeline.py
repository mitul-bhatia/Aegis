import sys
import os
import json
import pytest

# Ensure tests use an isolated test database
os.environ["DATABASE_URL"] = "sqlite:///./test_aegis.db"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal, init_db
from backend.app.models.entities import User, Repository, Scan, Issue

client = TestClient(app)


def test_full_aegis_pipeline_lifecycle():
    init_db()
    
    # 1. Test Health
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. Test Get Me (Auth)
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 200
    user_data = res.json()
    assert "github_username" in user_data
    user_id = user_data["id"]

    # 3. Test List Available Repos
    res = client.get(f"/api/v1/repos/available?user_id={user_id}")
    assert res.status_code == 200
    available_repos = res.json()
    assert len(available_repos) > 0

    # 4. Test Add Repository
    res = client.post("/api/v1/repos", json={"user_id": user_id, "repo_url": "https://github.com/mitu1046/aegis-test-repo"})
    assert res.status_code == 200
    repo = res.json()
    repo_id = repo["id"]
    assert repo["full_name"] == "mitu1046/aegis-test-repo"

    # 5. Test Trigger Direct Scan
    res = client.post(f"/api/v1/scans/trigger-direct?repo_id={repo_id}&commit_sha=HEAD&branch=main")
    assert res.status_code == 200
    trigger_result = res.json()
    assert "queued" in trigger_result["message"]

    # 6. Test List Scans
    res = client.get(f"/api/v1/scans?repo_id={repo_id}")
    assert res.status_code == 200
    scans_paginated = res.json()
    assert len(scans_paginated["data"]) > 0
    scan_id = scans_paginated["data"][0]["id"]

    # 7. Test Get Scan Detail
    res = client.get(f"/api/v1/scans/{scan_id}")
    assert res.status_code == 200
    scan_detail = res.json()
    assert scan_detail["id"] == scan_id

    # 8. Test Approve & Fix Scan
    res = client.post(f"/api/v1/scans/{scan_id}/approve", json={"user_context": "Make sure to use parameterized SQL query."})
    assert res.status_code == 200
    assert "initiated" in res.json()["message"]

    # 9. Test SARIF Export
    res = client.get(f"/api/v1/scans/{scan_id}/sarif")
    assert res.status_code == 200
    sarif = res.json()
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) > 0

    # 10. Test Intelligence & Stats
    res = client.get(f"/api/v1/stats?user_id={user_id}")
    assert res.status_code == 200
    assert "total_repos" in res.json()

    res = client.get(f"/api/v1/intelligence/repo/{repo_id}")
    assert res.status_code == 200
    assert "threat_level" in res.json()

    print("\n[✔] ALL 10 END-TO-END PIPELINE TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    test_full_aegis_pipeline_lifecycle()
