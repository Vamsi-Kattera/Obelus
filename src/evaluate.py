"""ClauseLens step 3: one scoring harness for every method.

A method is any function  predict(text, clause) -> Prediction.
The harness scores it the same way every time, so BM25, the LLM and the hybrid
can be compared fairly.

Presence:  did the system correctly say the clause is there / not there?
Span:      when it found the clause, how many characters overlap the experts' labels?
"""
from dataclasses import dataclass, field

from chunk import overlaps


@dataclass
class Prediction:
    found: bool
    spans: list = field(default_factory=list)   # list of (start, end)
    score: float = 0.0                          # confidence, higher = more sure


def _merge(spans):
    """Merge overlapping character ranges so characters are counted once."""
    out = []
    for s, e in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def _overlap_chars(a, b):
    total = 0
    for s1, e1 in _merge(a):
        for s2, e2 in _merge(b):
            if overlaps(s1, e1, s2, e2):
                total += min(e1, e2) - max(s1, s2)
    return total


def _length(spans):
    return sum(e - s for s, e in _merge(spans))


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def score(contracts, clause, predict):
    """Run `predict` on every contract and return presence and span metrics."""
    tp = fp = fn = tn = 0
    span_overlap = span_pred = span_gold = 0
    for c in contracts:
        gold = c.spans.get(clause, [])
        pred = predict(c.text, clause)
        if pred.found and gold:
            tp += 1
        elif pred.found and not gold:
            fp += 1
        elif not pred.found and gold:
            fn += 1
        else:
            tn += 1
        if gold:                                   # span quality only where the clause exists
            span_gold += _length(gold)
            if pred.found:
                span_pred += _length(pred.spans)
                span_overlap += _overlap_chars(pred.spans, gold)
    p, r, f = prf(tp, fp, fn)
    sp, sr, sf = prf(span_overlap, span_pred - span_overlap, span_gold - span_overlap)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "presence_precision": p, "presence_recall": r, "presence_f1": f,
            "span_precision": sp, "span_recall": sr, "span_f1": sf}


def tune_threshold(contracts, clause, scorer):
    """Pick the score threshold with the best presence F1 on `contracts` (use the train split).
    `scorer(text, clause)` must return (score, spans) for the best candidate."""
    rows = []
    for c in contracts:
        s, spans = scorer(c.text, clause)
        rows.append((s, bool(c.spans.get(clause))))
    best_t, best_f = 0.0, -1.0
    for t in sorted({s for s, _ in rows}):
        tp = sum(1 for s, g in rows if s >= t and g)
        fp = sum(1 for s, g in rows if s >= t and not g)
        fn = sum(1 for s, g in rows if s < t and g)
        f = prf(tp, fp, fn)[2]
        if f > best_f:
            best_t, best_f = t, f
    return best_t, best_f


def print_report(name, clause, m):
    print(f"\n{name} | {clause}")
    print(f"  confusion: TP={m['tp']} FP={m['fp']} FN={m['fn']} TN={m['tn']}")
    print(f"  presence : precision {m['presence_precision']:.0%}  recall {m['presence_recall']:.0%}  F1 {m['presence_f1']:.0%}")
    print(f"  spans    : precision {m['span_precision']:.0%}  recall {m['span_recall']:.0%}  F1 {m['span_f1']:.0%}")
