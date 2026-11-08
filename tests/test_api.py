"""HTTP-level tests. They need fastapi and httpx (see requirements-dev.txt) and no API key."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

import api
from llm import DailyQuotaError

QUOTE = "In no event shall either party's liability exceed the fees paid in the prior twelve months."
TEXT = "Intro about the parties. " * 20 + QUOTE + " " + "Filler about delivery. " * 50


@pytest.fixture()
def client():
    api.app.dependency_overrides[api.get_llm] = lambda: (lambda p, s: {"found": True, "quotes": [QUOTE]})
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_clauses_lists_measured_and_supported(client):
    body = client.get("/clauses").json()
    assert "Cap On Liability" in body["measured"] and "Non-Compete" in body["supported"]


def test_analyze_ok(client):
    r = client.post("/analyze", json={"text": TEXT, "clauses": ["Cap On Liability"]})
    assert r.status_code == 200
    first = r.json()["results"][0]
    assert first["found"] and first["passages"][0]["text"].startswith("In no event")


def test_wrong_method_is_405(client):
    assert client.get("/analyze").status_code == 405


def test_validation_is_422(client):
    assert client.post("/analyze", json={"text": ""}).status_code == 422
    assert client.post("/analyze", json={"text": TEXT, "clauses": ["Nope"]}).status_code == 422


def test_token_is_enforced_when_set(client, monkeypatch):
    monkeypatch.setenv("CLAUSELENS_API_TOKEN", "secret")
    body = {"text": TEXT, "clauses": ["Cap On Liability"]}
    assert client.post("/analyze", json=body).status_code == 401
    assert client.post("/analyze", json=body, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/analyze", json=body, headers={"X-API-Key": "secret"}).status_code == 200


def test_quota_error_becomes_503():
    def broke(p, s):
        raise DailyQuotaError("used up")
    api.app.dependency_overrides[api.get_llm] = lambda: broke
    try:
        r = TestClient(api.app).post("/analyze", json={"text": TEXT, "clauses": ["Cap On Liability"]})
        assert r.status_code == 503
    finally:
        api.app.dependency_overrides.clear()
