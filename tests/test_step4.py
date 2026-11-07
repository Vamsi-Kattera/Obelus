import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from extract import build_prompt, extract, locate
from llm import call_with_retries

TEXT = ("Intro text about the parties.\n\nIn no event shall either party's\nliability exceed the fees paid "
        "in the prior twelve months.\n\n" + "Filler sentence about delivery. " * 100)
QUOTE = "In no event shall either party's liability exceed the fees paid in the prior twelve months."


def test_locate_ignores_line_breaks():
    s, e = locate(QUOTE, TEXT)
    assert "liability exceed" in TEXT[s:e]
    assert TEXT[s:].startswith("In no event")


def test_locate_returns_none_for_invented_text():
    assert locate("The supplier is liable for everything forever.", TEXT) is None


def test_extract_keeps_grounded_quote():
    pred = extract(TEXT, "Cap On Liability", lambda p, s: {"found": True, "quotes": [QUOTE]})
    assert pred.found and len(pred.spans) == 1


def test_extract_abstains_on_hallucinated_quote():
    fake = lambda p, s: {"found": True, "quotes": ["Liability is capped at one million pounds."]}
    pred = extract(TEXT, "Cap On Liability", fake)
    assert not pred.found and pred.spans == []


def test_extract_respects_not_found():
    pred = extract(TEXT, "Cap On Liability", lambda p, s: {"found": False, "quotes": []})
    assert not pred.found


def test_prompt_contains_rules_and_excerpt():
    p = build_prompt("Cap On Liability", [(0, 5, "hello")])
    assert "EXACTLY" in p and "[Excerpt 1]" in p and "hello" in p


def test_retry_recovers_from_temporary_error():
    calls = {"n": 0}
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("503 UNAVAILABLE: model overloaded")
        return "ok"
    assert call_with_retries(flaky, sleep=lambda s: None) == "ok" and calls["n"] == 3


def test_retry_does_not_hide_real_errors():
    def bad():
        raise ValueError("bad schema")
    with pytest.raises(ValueError):
        call_with_retries(bad, sleep=lambda s: None)


def test_diagnose_sorts_outcomes():
    from data import Contract
    from diagnose import diagnose_one
    start, end = locate(QUOTE, TEXT)
    c = Contract("t", TEXT, {"Cap On Liability": [(start, end)]})
    assert diagnose_one(c, "Cap On Liability", lambda p, s: {"found": True, "quotes": [QUOTE]})["reason"] == "ok"
    assert diagnose_one(c, "Cap On Liability", lambda p, s: {"found": False, "quotes": []})["reason"] == "llm_said_no"
    bad = diagnose_one(c, "Cap On Liability", lambda p, s: {"found": True, "quotes": ["made up"]})
    assert bad["reason"] == "quote_not_grounded" and bad["ungrounded_quotes"] == ["made up"]


def test_diagnose_flags_retrieval_miss():
    from data import Contract
    from diagnose import diagnose_one
    far_text = ("Payment terms and delivery schedule apply. " * 400) + QUOTE
    s, e = locate(QUOTE, far_text)
    far = Contract("f", far_text, {"Cap On Liability": [(s, e)]})
    r = diagnose_one(far, "Zzz Unknown Clause", lambda p, s: {"found": False, "quotes": []}, top_k=1)
    assert r["reason"] in ("retrieval_miss", "llm_said_no")


def test_false_positive_finder_skips_labelled_contracts():
    from data import Contract
    from check_false_positives import find_false_positives
    labelled = Contract("has", TEXT, {"Cap On Liability": [(0, 10)]})
    unlabelled = Contract("no", TEXT, {"Cap On Liability": []})
    saying_yes = lambda p, s: {"found": True, "quotes": [QUOTE]}
    out = find_false_positives([labelled, unlabelled], "Cap On Liability", saying_yes)
    assert [t for t, _ in out] == ["no"] and "liability" in out[0][1][0]
    saying_no = lambda p, s: {"found": False, "quotes": []}
    assert find_false_positives([unlabelled], "Cap On Liability", saying_no) == []


def test_cache_avoids_second_api_call(tmp_path):
    from llm import cached
    from extract import ClauseAnswer
    calls = {"n": 0}
    def fake(prompt, schema):
        calls["n"] += 1
        return {"found": True, "quotes": ["q"]}
    path = tmp_path / "c.json"
    wrapped = cached(fake, path)
    assert wrapped("hello", ClauseAnswer) == {"found": True, "quotes": ["q"]}
    assert wrapped("hello", ClauseAnswer)["found"] is True
    assert calls["n"] == 1                      # second identical question came from the cache
    wrapped("different prompt", ClauseAnswer)
    assert calls["n"] == 2                      # new prompt asks the model again
    again = cached(fake, path)                  # a fresh wrapper reloads the file from disk
    again("hello", ClauseAnswer)
    assert calls["n"] == 2


def test_span_stats_classifies_overlap():
    from data import Contract
    from evaluate import Prediction
    from span_stats import span_stats, summarise
    c = Contract("a", "x" * 1000, {"K": [(100, 300)]})
    good = span_stats([c], "K", lambda t, k: Prediction(True, [(100, 300)]))
    part = span_stats([c], "K", lambda t, k: Prediction(True, [(100, 150)]))
    none = span_stats([c], "K", lambda t, k: Prediction(True, [(500, 600)]))
    skip = span_stats([c], "K", lambda t, k: Prediction(False))
    assert summarise(good)["good"] == 1 and summarise(part)["partial"] == 1
    assert summarise(none)["no_overlap"] == 1 and skip == []