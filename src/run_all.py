"""Run the three methods on several clauses and write a results table.

Run from C:\\dev\\clauselens (key set in your terminal):
    python src\\run_all.py
    python src\\run_all.py --clauses "Audit Rights" "Non-Compete"

The table is saved to eval\\results.md after every clause, so a long run is never lost.
Answers come from eval\\llm_cache.json when they exist.
"""
import argparse
import time
from pathlib import Path

from evaluate import Prediction, score, tune_threshold
from extract import extract
from run_bm25_eval import best_chunk

DEFAULT_CLAUSES = ["Cap On Liability", "Termination For Convenience", "Audit Rights", "Anti-Assignment"]
METHODS = ["1. BM25", "2. BM25 + LLM", "3. BM25 gate + LLM"]


def evaluate_clause(clause, parts, llm, split="dev", top_k=6):
    """Return {method: metrics} plus counts of contracts with and without the clause."""
    data = parts[split]
    thr, _ = tune_threshold(parts["train"], clause, best_chunk)

    def m1(text, c):
        s, spans = best_chunk(text, c)
        return Prediction(s >= thr, spans if s >= thr else [], s)

    def m2(text, c):
        return extract(text, c, llm, top_k=top_k)

    def m3(text, c):
        s, _ = best_chunk(text, c)
        return Prediction(False, [], s) if s < thr else extract(text, c, llm, top_k=top_k)

    out = {name: score(data, clause, fn) for name, fn in zip(METHODS, (m1, m2, m3))}
    n_pos = sum(1 for c in data if c.spans.get(clause))
    return {"n_pos": n_pos, "n_neg": len(data) - n_pos, "metrics": out}


def format_table(results, split="dev"):
    lines = [f"Results on the {split} split (presence = is the clause there; span = does the quote match the experts' text)", "",
             "| Clause | With / without | Method | Presence P | Presence R | Presence F1 | Span P | Span R | Span F1 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for clause, r in results.items():
        for name in METHODS:
            m = r["metrics"][name]
            lines.append(f"| {clause} | {r['n_pos']} / {r['n_neg']} | {name} | "
                         f"{m['presence_precision']:.0%} | {m['presence_recall']:.0%} | {m['presence_f1']:.0%} | "
                         f"{m['span_precision']:.0%} | {m['span_recall']:.0%} | {m['span_f1']:.0%} |")
    return "\n".join(lines)


def main():
    from data import load_contracts, split_contracts
    from llm import DailyQuotaError, cached, gemini_json

    ap = argparse.ArgumentParser()
    ap.add_argument("--clauses", nargs="+", default=DEFAULT_CLAUSES)
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--delay", type=float, default=4.0)
    ap.add_argument("--top-k", type=int, default=6)
    args = ap.parse_args()

    parts = split_contracts(load_contracts()[0])
    calls = {"n": 0}

    def slow(prompt, schema):
        calls["n"] += 1
        time.sleep(args.delay)
        return gemini_json(prompt, schema)

    llm = cached(slow)
    results = {}
    for clause in args.clauses:
        print(f"Running {clause} ...", flush=True)
        try:
            results[clause] = evaluate_clause(clause, parts, llm, args.split, args.top_k)
        except DailyQuotaError as exc:
            print(f"\nStopped at '{clause}': {exc}")
            break
        Path("eval").mkdir(exist_ok=True)
        Path("eval/results.md").write_text(format_table(results, args.split), encoding="utf-8")
    if results:
        print("\n" + format_table(results, args.split))
    print(f"\nNew API calls: {calls['n']}. Table saved to eval\\results.md")


if __name__ == "__main__":
    main()