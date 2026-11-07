import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data import Contract
from evaluate import Prediction, prf, score, tune_threshold


def contracts():
    return [
        Contract("a", "x" * 100, {"Cap": [(10, 30)]}),   # clause present
        Contract("b", "x" * 100, {"Cap": []}),           # absent
        Contract("c", "x" * 100, {"Cap": [(50, 60)]}),   # present
        Contract("d", "x" * 100, {"Cap": []}),           # absent
    ]


def test_prf_basic():
    p, r, f = prf(8, 2, 2)
    assert abs(p - 0.8) < 1e-9 and abs(r - 0.8) < 1e-9 and abs(f - 0.8) < 1e-9
    assert prf(0, 0, 0) == (0.0, 0.0, 0.0)


def test_perfect_predictor_scores_one():
    cs = contracts()
    it = iter(cs)
    def perfect(text, clause):
        c = next(it)
        return Prediction(bool(c.spans["Cap"]), list(c.spans["Cap"]))
    m = score(cs, "Cap", perfect)
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (2, 0, 0, 2)
    assert m["presence_f1"] == 1.0 and m["span_f1"] == 1.0


def test_always_yes_has_perfect_recall_and_half_precision():
    m = score(contracts(), "Cap", lambda t, c: Prediction(True, [(0, 100)]))
    assert m["presence_recall"] == 1.0
    assert abs(m["presence_precision"] - 0.5) < 1e-9
    assert m["span_recall"] == 1.0
    assert m["span_precision"] < 0.5


def test_always_no_has_zero_recall():
    m = score(contracts(), "Cap", lambda t, c: Prediction(False))
    assert m["presence_recall"] == 0.0 and m["tn"] == 2 and m["fn"] == 2


def test_tune_threshold_separates_classes():
    cs = contracts()
    scores = {"a": 9.0, "b": 1.0, "c": 8.0, "d": 2.0}
    order = iter(cs)
    def scorer(text, clause):
        c = next(order)
        return scores[c.title], []
    thr, f1 = tune_threshold(cs, "Cap", scorer)
    assert 2.0 < thr <= 8.0 and f1 == 1.0
