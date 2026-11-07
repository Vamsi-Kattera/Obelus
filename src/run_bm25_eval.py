"""Score the BM25 baseline with a tuned 'is it there?' threshold.

Run from C:\\dev\\clauselens:
    python src\\run_bm25_eval.py "Cap On Liability"
"""
import argparse

from baseline_bm25 import QUERIES, tokenize
from chunk import make_chunks
from data import load_contracts, split_contracts
from evaluate import Prediction, print_report, score, tune_threshold
from rank_bm25 import BM25Okapi


def best_chunk(text, clause, size=1200, step=600):
    """Return (bm25 score, [(start, end)]) for the top chunk."""
    chunks = make_chunks(text, size, step)
    bm25 = BM25Okapi([tokenize(c[2]) for c in chunks])
    scores = bm25.get_scores(tokenize(QUERIES.get(clause, clause)))
    i = max(range(len(chunks)), key=lambda j: scores[j])
    return float(scores[i]), [(chunks[i][0], chunks[i][1])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clause")
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    args = ap.parse_args()

    contracts, _ = load_contracts()
    parts = split_contracts(contracts)
    thr, f1 = tune_threshold(parts["train"], args.clause, best_chunk)
    print(f"Threshold tuned on train ({len(parts['train'])} contracts): {thr:.2f} (train presence F1 {f1:.0%})")

    def predict(text, clause):
        s, spans = best_chunk(text, clause)
        return Prediction(found=s >= thr, spans=spans if s >= thr else [], score=s)

    print_report(f"BM25 baseline on {args.split}", args.clause, score(parts[args.split], args.clause, predict))


if __name__ == "__main__":
    main()
