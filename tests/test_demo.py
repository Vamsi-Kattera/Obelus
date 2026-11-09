"""Demo-mode tests for the HTTP layer. Need fastapi and httpx; no API key."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

import api
from limits import DemoLimiter

QUOTE = "In no event shall either party's liability exceed the fees paid in the prior twelve months."
TEXT = "Intro about the parties. " * 20 + QUOTE + " " + "Filler about delivery. " * 50


@pytest.fixture()
def demo(monkeypatch):
    monkeypatch.setenv("OBELUS_DEMO", "1")
    monkeypatch.setattr(api, "limiter", DemoLimiter(per_visitor=2, window_s=3600, daily_cap=100))
    api.app.dependency_overrides[api.get_llm] = lambda: (lambda p, s: {"found": True, "quotes": [QUOTE]})
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


def body(**kw):
    return {"text": TEXT, "clauses": ["Cap On Liability"], **kw}


def test_health_reports_demo_limits(demo):
    h = demo.get("/health").json()
    assert h["demo"] is True and h["max_chars"] == api.DEMO_MAX_CHARS and h["max_clauses"] == api.DEMO_MAX_CLAUSES


def test_third_request_from_same_visitor_is_429(demo):
    assert demo.post("/analyze", json=body()).status_code == 200
    assert demo.post("/analyze", json=body()).status_code == 200
    r = demo.post("/analyze", json=body())
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_forwarded_header_separates_visitors(demo):
    for _ in range(2):
        assert demo.post("/analyze", json=body(), headers={"x-forwarded-for": "1.1.1.1"}).status_code == 200
    assert demo.post("/analyze", json=body(), headers={"x-forwarded-for": "1.1.1.1"}).status_code == 429
    assert demo.post("/analyze", json=body(), headers={"x-forwarded-for": "2.2.2.2"}).status_code == 200


def test_too_long_is_413_and_does_not_use_quota(demo):
    big = {"text": "x" * (api.DEMO_MAX_CHARS + 1), "clauses": ["Cap On Liability"]}
    assert demo.post("/analyze", json=big).status_code == 413
    assert demo.post("/analyze", json=body()).status_code == 200
    assert demo.post("/analyze", json=body()).status_code == 200


def test_clause_count_is_limited_and_required(demo):
    four = ["Cap On Liability", "Termination For Convenience", "Audit Rights", "Anti-Assignment"]
    assert demo.post("/analyze", json=body(clauses=four)).status_code == 422
    assert demo.post("/analyze", json={"text": TEXT}).status_code == 422


def test_home_page_is_served(demo):
    r = demo.get("/")
    assert r.status_code == 200 and "Obelus" in r.text


def test_demo_off_has_no_limits(monkeypatch):
    monkeypatch.delenv("OBELUS_DEMO", raising=False)
    api.app.dependency_overrides[api.get_llm] = lambda: (lambda p, s: {"found": True, "quotes": [QUOTE]})
    c = TestClient(api.app)
    for _ in range(8):
        assert c.post("/analyze", json={"text": TEXT, "clauses": ["Cap On Liability"]}).status_code == 200
    api.app.dependency_overrides.clear()
