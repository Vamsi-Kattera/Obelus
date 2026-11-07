"""Why did the LLM extractor miss clauses that are really there?

For every dev contract that HAS the clause, sort the outcome into one reason:
  ok                 found and grounded
  retrieval_miss     the clause was not inside the chunks we showed the model
  llm_said_no        the clause WAS shown, but the model answered found=false
  quote_not_grounded the model quoted something we could not find in the contract

Run from C:\\dev\\clauselens (key set in your terminal):
    python src\\diagnose.py "Cap On Liability" --limit 30
Results are saved to eval\\diagnose_<clause>.json so you can read the raw answers.
"""
import argparse
import json
import time
from collections import Counter
from pathlib import Path

from baseline_bm25 import QUERIES, rank_chunks
from chunk import make_chunks, overlaps
from extract import ClauseAnswer, build_prompt, locate


def diagnose_one(contract, clause, llm, top_k=3, size=1200, step=600):
    gold = contract.spans.get(clause, [])
    chunks = make_chunks(contract.text, size, step)
    order = rank_chunks(chunks, QUERIES.get(clause, clause))[:top_k]
    shown = [chunks[i] for i in sorted(order)]
    in_shown = any(overlaps(c[0], c[1], s, e) for c in shown for s, e in gold)
    answer = ClauseAnswer(**llm(build_prompt(clause, shown), ClauseAnswer))
    grounded = [q for q in answer.quotes if locate(q, contract.text)]
    if answer.found and grounded:
        reason = "ok"
    elif not in_shown:
        reason = "retrieval_miss"
    elif not answer.found:
        reason = "llm_said_no"
    else:
        reason = "quote_not_grounded"
    return {"title": contract.title, "reason": reason, "clause_in_shown_chunks": in_shown,
            "found": answer.found, "quotes": answer.quotes,
            "ungrounded_quotes": [q for q in answer.quotes if q not in grounded],
            "gold_text": [contract.text[s:e][:300] for s, e in gold][:2]}


def main():
    from data import load_contracts, split_contracts
    from llm import gemini_json

    ap = argparse.ArgumentParser()
    ap.add_argument("clause")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--delay", type=float, default=4.0)
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()

    contracts, _ = load_contracts()
    dev = split_contracts(contracts)["dev"][: args.limit]
    positives = [c for c in dev if c.spans.get(args.clause)]
    print(f"{len(positives)} of {len(dev)} dev contracts have '{args.clause}'. One call each.")

    rows = []
    for c in positives:
        time.sleep(args.delay)
        rows.append(diagnose_one(c, args.clause, gemini_json, top_k=args.top_k))

    counts = Counter(r["reason"] for r in rows)
    print("\nOutcome for contracts that HAVE the clause:")
    for reason in ("ok", "retrieval_miss", "llm_said_no", "quote_not_grounded"):
        print(f"  {reason:20} {counts.get(reason, 0)}")

    Path("eval").mkdir(exist_ok=True)
    out = Path("eval") / f"diagnose_{args.clause.replace(' ', '_')}.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nRaw answers saved to {out}")

    for r in rows:
        if r["reason"] == "quote_not_grounded":
            print("\nExample of a dropped quote:")
            print("  model quoted :", (r["ungrounded_quotes"] or ["?"])[0][:200])
            print("  experts label:", (r["gold_text"] or ["?"])[0][:200])
            break


if __name__ == "__main__":
    main()
