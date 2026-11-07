import pytest
from fastapi.testclient import TestClient
from plcodestore import studio
from plcodestore.review import CHECKS

@pytest.fixture
def client(tmp_path):
    studio.configure(tmp_path/"review.db")
    return TestClient(studio.app)

def test_studio_serves_review_page(client):
    r=client.get("/")
    assert r.status_code==200 and "Review Studio" in r.text

def test_api_rejects_unknown_project(client):
    r=client.post("/api/cards/missing/decision",json={"digest":"xyz","action":"approved","checks":list(CHECKS)})
    assert r.status_code==404

def test_cors_nonlocal_origin_forbidden(client):
    r=client.post("/api/cards/abc/decision",headers={"Origin":"https://evil.example"},json={"digest":"abc","action":"approved"})
    assert r.status_code==403
