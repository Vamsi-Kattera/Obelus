"""Why is span recall low? Compare the length of what the experts labelled with what the model quoted.
Uses the cache, so it makes no API calls once run_llm_eval has been run.

Run from C:\\dev\\clauselens:
    python src\\span_stats.py "Cap On Liability"
"""
import argparse

from evaluate import _length, _overlap_chars
from extract import extract


def span_stats(contracts, clause, predict):
    """Only contracts where the clause exists AND the model said found."""
    rows = []
    for c in contracts:
        gold = c.spans.get(clause, [])
        if not gold:
            continue
        pred = predict(c.text, clause)
        if not pred.found:
            continue
        g, p = _length(gold), _length(pred.spans)
        o = _overlap_chars(pred.spans, gold)
        rows.append({"title": c.title, "gold": g, "pred": p, "overlap": o})
    return rows


def summarise(rows):
    n = len(rows)
    if not n:
        return {"n": 0}
    return {
        "n": n,
        "avg_gold_chars": sum(r["gold"] for r in rows) / n,
        "avg_pred_chars": sum(r["pred"] for r in rows) / n,
        "no_overlap": sum(1 for r in rows if r["overlap"] == 0),
        "partial": sum(1 for r in rows if 0 < r["overlap"] < 0.8 * r["gold"]),
        "good": sum(1 for r in rows if r["overlap"] >= 0.8 * r["gold"]),
    }


def main():
    from data import load_contracts, split_contracts
    from llm import cached, gemini_json

    ap = argparse.ArgumentParser()
    ap.add_argument("clause")
    ap.add_argument("--top-k", type=int, default=6)
    args = ap.parse_args()

    dev = split_contracts(load_contracts()[0])["dev"]
    store = cached(gemini_json)
    rows = span_stats(dev, args.clause, lambda t, c: extract(t, c, store, top_k=args.top_k))
    s = summarise(rows)
    print(f"Contracts with the clause where the model said found: {s['n']}")
    print(f"Average labelled length : {s['avg_gold_chars']:.0f} characters")
    print(f"Average quoted length   : {s['avg_pred_chars']:.0f} characters")
    print(f"Quote covers >=80% of the label : {s['good']}")
    print(f"Quote covers only part of it    : {s['partial']}")
    print(f"Quote misses the label entirely : {s['no_overlap']}")


if __name__ == "__main__":
    main()
