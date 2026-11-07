"""Look at contracts the experts did NOT label, where the model claims the clause is present.
A 'false positive' is sometimes an expert miss, so read the quote and judge it yourself.

Run from C:\\dev\\clauselens (key set in your terminal):
    python src\\check_false_positives.py "Cap On Liability" --limit 30 --top-k 6
"""
import argparse
import time


def find_false_positives(contracts, clause, llm, top_k=6, delay=0.0, extract_fn=None):
    """Return [(title, [quotes])] for contracts without the clause where the model says found."""
    from extract import extract
    out = []
    for c in contracts:
        if c.spans.get(clause):
            continue
        if delay:
            time.sleep(delay)
        pred = extract(c.text, clause, llm, top_k=top_k)
        if pred.found:
            out.append((c.title, [c.text[s:e] for s, e in pred.spans]))
    return out


def main():
    from data import load_contracts, split_contracts
    from llm import gemini_json

    ap = argparse.ArgumentParser()
    ap.add_argument("clause")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--delay", type=float, default=4.0)
    args = ap.parse_args()

    dev = split_contracts(load_contracts()[0])["dev"][: args.limit]
    negatives = [c for c in dev if not c.spans.get(args.clause)]
    print(f"{len(negatives)} of {len(dev)} dev contracts have no '{args.clause}' label. One call each.")
    fps = find_false_positives(dev, args.clause, gemini_json, args.top_k, args.delay)
    for i, (title, quotes) in enumerate(fps, 1):
        print(f"\n[{i}] {title}")
        for q in quotes[:2]:
            print("   model quoted:", " ".join(q.split())[:350])
    print(f"\n{len(fps)} possible false positives. For each, decide: is the quote really this clause?")


if __name__ == "__main__":
    main()
