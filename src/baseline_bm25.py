"""ClauseLens step 2: a BM25 baseline for finding one clause type.

Run from C:\\dev\\clauselens:
    python src\\baseline_bm25.py "Cap On Liability"
    python src\\baseline_bm25.py "Governing Law" --split dev
"""
import argparse
import re
from math import comb

from rank_bm25 import BM25Okapi

from chunk import make_chunks, overlaps

# Hand-written search words per clause. Unknown clauses fall back to the clause name.
QUERIES = {
    "Cap On Liability": "liability shall not exceed cap limited aggregate total liability amount fees paid limitation limitation of liability in no event liable damages claims brought within months consequential indirect special incidental punitive lost profits",
    "Governing Law": "governed by construed in accordance with laws of the state governing law jurisdiction",
    "Termination For Convenience": "terminate this agreement at any time for convenience without cause upon written notice days",
    "Audit Rights": "audit inspect examine books records access during normal business hours",
    "Anti-Assignment": "may not assign transfer agreement rights without prior written consent",
    "Non-Compete": "shall not compete directly or indirectly competing business restricted",
    "Exclusivity": "exclusive exclusively sole right only shall not appoint another",
}


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def rank_chunks(chunks, query):
    """Return chunk indexes, best first."""
    bm25 = BM25Okapi([tokenize(c[2]) for c in chunks])
    scores = bm25.get_scores(tokenize(query))
    return sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)


def chunk_hits_gold(chunk, gold_spans):
    return any(overlaps(chunk[0], chunk[1], s, e) for s, e in gold_spans)


def random_hit_prob(n_chunks, n_gold_chunks, k):
    """Chance that k randomly chosen chunks include at least one gold chunk."""
    k = min(k, n_chunks)
    if n_gold_chunks == 0:
        return 0.0
    if n_chunks - n_gold_chunks < k:
        return 1.0
    return 1 - comb(n_chunks - n_gold_chunks, k) / comb(n_chunks, k)


def evaluate(contracts, clause, ks=(1, 3, 5), size=1200, step=600):
    """Hit@k over contracts where the clause is present, plus the random-guess rate."""
    query = QUERIES.get(clause, clause)
    hits = {k: 0 for k in ks}
    rand = {k: 0.0 for k in ks}
    present = absent = 0
    for c in contracts:
        gold = c.spans.get(clause, [])
        if not gold:
            absent += 1
            continue
        present += 1
        chunks = make_chunks(c.text, size, step)
        order = rank_chunks(chunks, query)
        gold_flags = [chunk_hits_gold(ch, gold) for ch in chunks]
        n_gold = sum(gold_flags)
        for k in ks:
            if any(gold_flags[i] for i in order[:k]):
                hits[k] += 1
            rand[k] += random_hit_prob(len(chunks), n_gold, k)
    return {"present": present, "absent": absent,
            "hit": {k: hits[k] / present if present else 0.0 for k in ks},
            "random": {k: rand[k] / present if present else 0.0 for k in ks}}


def main():
    from data import load_contracts, split_contracts   # only the command-line tool needs the dataset

    ap = argparse.ArgumentParser()
    ap.add_argument("clause")
    ap.add_argument("--split", default="dev", choices=["train", "dev", "test"])
    args = ap.parse_args()

    contracts, skipped = load_contracts()
    part = split_contracts(contracts)[args.split]
    print(f"Loaded {len(contracts)} contracts; {skipped} labels skipped (offset mismatch).")
    print(f"Split '{args.split}': {len(part)} contracts")
    r = evaluate(part, args.clause)
    print(f"\nClause: {args.clause}")
    print(f"Contracts with the clause: {r['present']}   without: {r['absent']}")
    print(f"{'k':>3} {'BM25 hit@k':>12} {'random hit@k':>14}")
    for k in r["hit"]:
        print(f"{k:>3} {r['hit'][k]:>12.0%} {r['random'][k]:>14.0%}")


if __name__ == "__main__":
    main()