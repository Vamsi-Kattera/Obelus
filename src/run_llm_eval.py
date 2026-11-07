"""Compare BM25 and BM25+LLM on the same dev contracts.

Run from C:\\dev\\clauselens (key set in your own terminal first):
    python src\\run_llm_eval.py "Cap On Liability" --limit 30
"""
import argparse
import time

from baseline_bm25 import QUERIES
from data import load_contracts, split_contracts
from evaluate import Prediction, print_report, score, tune_threshold
from extract import extract
from llm import gemini_json
from run_bm25_eval import best_chunk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clause")
    ap.add_argument("--limit", type=int, default=30, help="how many dev contracts to score (0 = all)")
    ap.add_argument("--delay", type=float, default=4.0, help="seconds between calls (free-tier limits)")
    ap.add_argument("--top-k", type=int, default=3, help="how many BM25 chunks to show the model")
    args = ap.parse_args()

    contracts, _ = load_contracts()
    parts = split_contracts(contracts)
    dev = parts["dev"][: args.limit] if args.limit else parts["dev"]
    print(f"Scoring {len(dev)} dev contracts (one Gemini call each).")

    thr, _ = tune_threshold(parts["train"], args.clause, best_chunk)

    def bm25_predict(text, clause):
        s, spans = best_chunk(text, clause)
        return Prediction(s >= thr, spans if s >= thr else [], s)

    def llm_predict(text, clause):
        time.sleep(args.delay)
        return extract(text, clause, gemini_json, top_k=args.top_k)

    print_report("BM25 baseline", args.clause, score(dev, args.clause, bm25_predict))
    print_report("BM25 + LLM quotes", args.clause, score(dev, args.clause, llm_predict))


if __name__ == "__main__":
    main()