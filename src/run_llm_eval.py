"""Compare three methods on the same dev contracts.

  1. BM25 baseline
  2. BM25 + LLM quotes
  3. BM25 gate + LLM quotes  (say 'found' only if BOTH agree)

Answers are cached in eval\\llm_cache.json, so re-running is free.

Run from C:\\dev\\clauselens (key set in your own terminal first):
    python src\\run_llm_eval.py "Cap On Liability" --limit 0 --top-k 6
"""
import argparse
import time

from data import load_contracts, split_contracts
from evaluate import Prediction, print_report, score, tune_threshold
from extract import extract
from llm import cached, gemini_json
from run_bm25_eval import best_chunk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clause")
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--limit", type=int, default=30, help="how many contracts to score (0 = all)")
    ap.add_argument("--delay", type=float, default=4.0, help="seconds between NEW API calls")
    ap.add_argument("--top-k", type=int, default=6, help="how many BM25 chunks to show the model")
    args = ap.parse_args()

    contracts, _ = load_contracts()
    parts = split_contracts(contracts)
    data = parts[args.split][: args.limit] if args.limit else parts[args.split]
    print(f"Scoring {len(data)} {args.split} contracts.")

    thr, _ = tune_threshold(parts["train"], args.clause, best_chunk)

    calls = {"n": 0}

    def slow_llm(prompt, schema):
        calls["n"] += 1
        time.sleep(args.delay)
        return gemini_json(prompt, schema)

    store = cached(slow_llm)

    def bm25_predict(text, clause):
        s, spans = best_chunk(text, clause)
        return Prediction(s >= thr, spans if s >= thr else [], s)

    def llm_predict(text, clause):
        return extract(text, clause, store, top_k=args.top_k)

    def gated_predict(text, clause):
        s, _ = best_chunk(text, clause)
        if s < thr:
            return Prediction(False, [], s)
        return extract(text, clause, store, top_k=args.top_k)

    print_report("1. BM25 baseline", args.clause, score(data, args.clause, bm25_predict))
    print_report("2. BM25 + LLM quotes", args.clause, score(data, args.clause, llm_predict))
    print_report("3. BM25 gate + LLM quotes", args.clause, score(data, args.clause, gated_predict))
    print(f"\nNew API calls this run: {calls['n']} (the rest came from the cache)")


if __name__ == "__main__":
    main()