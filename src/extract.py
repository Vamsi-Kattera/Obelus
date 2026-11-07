"""ClauseLens step 4: BM25 finds candidate chunks, an LLM quotes the clause, and we
only trust quotes that really appear in the contract (cite or abstain)."""
import re

from pydantic import BaseModel, Field

from baseline_bm25 import QUERIES, rank_chunks
from chunk import make_chunks
from evaluate import Prediction

DESCRIPTIONS = {
    "Cap On Liability": ("any limit or exclusion of a party's liability for breach. This includes: a maximum amount "
                         "that can be recovered (for example 'liability shall not exceed the fees paid'); a time limit "
                         "for bringing claims; and an exclusion of certain kinds of damages, such as indirect, "
                         "consequential, special, incidental or punitive damages or lost profits"),
    "Governing Law": "which country's or state's law governs the agreement",
    "Termination For Convenience": "a right to end the agreement at any time without needing a reason, usually on notice",
    "Audit Rights": "a right to inspect or audit the other party's books, records or facilities",
    "Anti-Assignment": "a rule that a party cannot assign or transfer the agreement without consent",
    "Non-Compete": "a restriction stopping a party from competing with the other party",
    "Exclusivity": "an exclusive right, or a promise not to deal with others",
}


class ClauseAnswer(BaseModel):
    found: bool = Field(description="true only if the clause appears in the excerpts")
    quotes: list[str] = Field(default_factory=list,
                              description="exact sentences copied from the excerpts; empty if not found")


def build_prompt(clause, chunks):
    what = DESCRIPTIONS.get(clause, clause)
    excerpts = "\n\n".join(f"[Excerpt {i + 1}]\n{c[2]}" for i, c in enumerate(chunks))
    return (
        "You review commercial contracts. Decide whether the excerpts contain this clause type:\n"
        f"{clause}: {what}\n\n"
        "Rules:\n"
        "- Copy the relevant sentences EXACTLY as written. Do not paraphrase or fix typos.\n"
        "- Quote the COMPLETE provision: every consecutive sentence that belongs to this clause, including\n"
        "  exceptions and wording such as 'provided that', 'except' or 'notwithstanding'. Skip unrelated sentences.\n"
        "- If the clause is not in the excerpts, return found=false and an empty list.\n"
        "- If a sentence limits or excludes liability in the way described, return it, even if it is not a money amount.\n"
        "- Never invent text.\n\n"
        f"{excerpts}"
    )


def locate(quote, text):
    """Find `quote` in `text`, ignoring differences in spaces and line breaks.
    Returns (start, end) in the original text, or None if it is not there."""
    words = quote.split()
    if not words:
        return None
    pattern = r"\s+".join(re.escape(w) for w in words)
    m = re.search(pattern, text)
    return (m.start(), m.end()) if m else None


def extract(text, clause, llm, top_k=3, size=1200, step=600):
    """llm(prompt, schema) -> dict with 'found' and 'quotes'. Returns a Prediction."""
    chunks = make_chunks(text, size, step)
    order = rank_chunks(chunks, QUERIES.get(clause, clause))[:top_k]
    shown = [chunks[i] for i in sorted(order)]          # keep contract order
    answer = ClauseAnswer(**llm(build_prompt(clause, shown), ClauseAnswer))
    if not answer.found:
        return Prediction(False)
    spans = [s for s in (locate(q, text) for q in answer.quotes) if s]
    if not spans:                                         # claimed a clause but no real quote: abstain
        return Prediction(False)
    return Prediction(True, spans, float(len(spans)))