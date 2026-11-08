"""Obelus service logic: no web framework in here, so it is easy to test.

analyze() takes a contract's text and a list of clause names and returns, for each clause,
whether it was found and the exact passages (with character positions in the original text).
Every passage is checked to exist in the contract: cite or abstain.
"""
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from extract import DESCRIPTIONS, extract

MAX_CHARS = 400_000     # roughly 130 pages of contract text
MAX_CLAUSES = 7

# Clauses whose accuracy was measured on the CUAD dev split (see eval/results.md).
EVALUATED = ["Cap On Liability", "Termination For Convenience", "Audit Rights", "Anti-Assignment"]
SUPPORTED = list(DESCRIPTIONS)
DISCLAIMER = ("Obelus highlights passages for a human reviewer. It is not legal advice and can miss "
              "clauses or flag the wrong text.")


class UnknownClause(ValueError):
    pass


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS, description="The contract text")
    clauses: Optional[list[str]] = Field(default=None, description="Clause names; default = the measured ones")

    @field_validator("text")
    @classmethod
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError("text must not be blank")
        return v


class Passage(BaseModel):
    start: int
    end: int
    text: str


class ClauseResult(BaseModel):
    clause: str
    found: bool
    passages: list[Passage]
    measured: bool          # True if this clause's accuracy was measured on CUAD


class AnalyzeResponse(BaseModel):
    results: list[ClauseResult]
    elapsed_ms: int
    disclaimer: str = DISCLAIMER


def resolve_clauses(requested):
    names = list(requested) if requested else list(EVALUATED)
    if len(names) > MAX_CLAUSES:
        raise UnknownClause(f"at most {MAX_CLAUSES} clauses per request")
    unknown = [n for n in names if n not in SUPPORTED]
    if unknown:
        raise UnknownClause(f"unknown clause(s): {', '.join(unknown)}")
    seen = []
    for n in names:
        if n not in seen:
            seen.append(n)
    return seen


def analyze(req, llm):
    """Run every requested clause (in parallel) and return an AnalyzeResponse."""
    start = time.perf_counter()
    names = resolve_clauses(req.clauses)

    def one(name):
        pred = extract(req.text, name, llm, top_k=6)
        passages = [Passage(start=s, end=e, text=req.text[s:e]) for s, e in pred.spans]
        return ClauseResult(clause=name, found=pred.found, passages=passages, measured=name in EVALUATED)

    with ThreadPoolExecutor(max_workers=min(4, len(names))) as pool:
        results = list(pool.map(one, names))
    return AnalyzeResponse(results=results, elapsed_ms=int((time.perf_counter() - start) * 1000))