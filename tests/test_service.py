import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from pydantic import ValidationError

from service import AnalyzeRequest, MAX_CLAUSES, UnknownClause, analyze, resolve_clauses

QUOTE = "In no event shall either party's liability exceed the fees paid in the prior twelve months."
TEXT = "Intro about the parties. " * 20 + QUOTE + " " + "Filler about delivery. " * 50


def yes(prompt, schema):
    return {"found": True, "quotes": [QUOTE]}


def no(prompt, schema):
    return {"found": False, "quotes": []}


def test_default_clauses_are_the_measured_ones():
    assert resolve_clauses(None) == ["Cap On Liability", "Termination For Convenience",
                                     "Audit Rights", "Anti-Assignment"]


def test_unknown_clause_is_rejected():
    with pytest.raises(UnknownClause):
        resolve_clauses(["Not A Clause"])


def test_too_many_clauses_rejected():
    with pytest.raises(UnknownClause):
        resolve_clauses(["Cap On Liability"] * (MAX_CLAUSES + 1))


def test_duplicates_are_removed_in_order():
    assert resolve_clauses(["Audit Rights", "Cap On Liability", "Audit Rights"]) == ["Audit Rights", "Cap On Liability"]


def test_analyze_returns_grounded_passages_with_positions():
    out = analyze(AnalyzeRequest(text=TEXT, clauses=["Cap On Liability"]), yes)
    r = out.results[0]
    assert r.found and r.measured
    p = r.passages[0]
    assert TEXT[p.start:p.end] == p.text and "liability exceed" in p.text
    assert "not legal advice" in out.disclaimer


def test_analyze_abstains_when_model_says_no():
    out = analyze(AnalyzeRequest(text=TEXT, clauses=["Audit Rights"]), no)
    assert not out.results[0].found and out.results[0].passages == []


def test_analyze_drops_invented_quotes():
    fake = lambda p, s: {"found": True, "quotes": ["The supplier pays unlimited damages forever."]}
    out = analyze(AnalyzeRequest(text=TEXT, clauses=["Cap On Liability"]), fake)
    assert not out.results[0].found


def test_unmeasured_clause_is_flagged():
    out = analyze(AnalyzeRequest(text=TEXT, clauses=["Non-Compete"]), no)
    assert out.results[0].measured is False


def test_results_keep_request_order_for_many_clauses():
    names = ["Anti-Assignment", "Cap On Liability", "Audit Rights", "Termination For Convenience"]
    out = analyze(AnalyzeRequest(text=TEXT, clauses=names), no)
    assert [r.clause for r in out.results] == names


def test_request_validation():
    with pytest.raises(ValidationError):
        AnalyzeRequest(text="")
    with pytest.raises(ValidationError):
        AnalyzeRequest(text="   \n ")
    with pytest.raises(ValidationError):
        AnalyzeRequest(text="x" * 400_001)
