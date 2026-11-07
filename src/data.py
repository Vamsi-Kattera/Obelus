"""Load CUAD and split it by contract (never by chunk, so test contracts stay unseen)."""
import json
import random
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Contract:
    title: str
    text: str
    # clause name -> list of (start, end) character spans labelled by experts
    spans: dict = field(default_factory=dict)


def find_cuad_json(root="data"):
    return next(Path(root).rglob("CUAD_v1.json"))


def parse_cuad(raw):
    """Turn the SQuAD-style CUAD json into Contract objects.
    Returns (contracts, skipped) where skipped counts labels whose text did not match the offsets."""
    contracts, skipped = [], 0
    for item in raw["data"]:
        para = item["paragraphs"][0]
        text = para["context"]
        spans = {}
        for qa in para["qas"]:
            clause = qa["id"].split("__")[-1]
            good = []
            for ans in qa["answers"]:
                start = ans["answer_start"]
                end = start + len(ans["text"])
                if text[start:end] == ans["text"]:
                    good.append((start, end))
                else:
                    skipped += 1
            spans[clause] = good
        contracts.append(Contract(item["title"], text, spans))
    return contracts, skipped


def load_contracts(path=None):
    path = Path(path) if path else find_cuad_json()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return parse_cuad(raw)


def split_contracts(contracts, seed=42, dev=0.2, test=0.2):
    """Deterministic split by contract: same seed gives the same split every time."""
    items = sorted(contracts, key=lambda c: c.title)
    random.Random(seed).shuffle(items)
    n_dev, n_test = int(len(items) * dev), int(len(items) * test)
    return {
        "dev": items[:n_dev],
        "test": items[n_dev:n_dev + n_test],
        "train": items[n_dev + n_test:],
    }
