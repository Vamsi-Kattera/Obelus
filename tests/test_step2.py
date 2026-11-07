import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from baseline_bm25 import evaluate, random_hit_prob
from chunk import make_chunks, overlaps
from data import parse_cuad, split_contracts


def fake_cuad(n=10):
    data = []
    for i in range(n):
        filler = "The parties agree to cooperate on deliveries and reports. " * 40
        clause = "In no event shall liability exceed the total fees paid in the prior twelve months."
        text = filler + clause + " " + filler
        start = text.index(clause)
        qas = [
            {"id": f"C{i}__Cap On Liability", "answers": [{"text": clause, "answer_start": start}]},
            {"id": f"C{i}__Governing Law", "answers": []},
        ]
        data.append({"title": f"C{i}", "paragraphs": [{"context": text, "qas": qas}]})
    return {"data": data}


def test_chunks_cover_text_and_overlap():
    text = "x" * 2500
    chunks = make_chunks(text, size=1000, step=500)
    assert chunks[0][:2] == (0, 1000)
    assert chunks[-1][1] == len(text)
    assert chunks[1][0] == 500


def test_overlaps():
    assert overlaps(0, 10, 9, 20)
    assert not overlaps(0, 10, 10, 20)


def test_parse_and_split_are_deterministic():
    contracts, skipped = parse_cuad(fake_cuad())
    assert skipped == 0 and len(contracts) == 10
    a = [c.title for c in split_contracts(contracts)["dev"]]
    b = [c.title for c in split_contracts(contracts)["dev"]]
    assert a == b and len(a) == 2


def test_bm25_finds_the_clause_better_than_random():
    contracts, _ = parse_cuad(fake_cuad())
    r = evaluate(contracts, "Cap On Liability")
    assert r["present"] == 10 and r["absent"] == 0
    assert r["hit"][1] == 1.0
    assert r["random"][1] < 0.5


def test_absent_clause_is_counted_not_scored():
    contracts, _ = parse_cuad(fake_cuad())
    r = evaluate(contracts, "Governing Law")
    assert r["present"] == 0 and r["absent"] == 10


def test_random_hit_prob_bounds():
    assert random_hit_prob(10, 0, 3) == 0.0
    assert random_hit_prob(10, 10, 3) == 1.0
    assert abs(random_hit_prob(4, 1, 2) - 0.5) < 1e-9
