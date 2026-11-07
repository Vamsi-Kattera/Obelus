"""Print the contracts where the model said 'not found' although the experts labelled the clause.
Reads the file written by diagnose.py. No API calls.

Run from C:\\dev\\clauselens:
    python src\\show_misses.py "Cap On Liability"
"""
import json
import sys
from pathlib import Path

clause = sys.argv[1] if len(sys.argv) > 1 else "Cap On Liability"
path = Path("eval") / f"diagnose_{clause.replace(' ', '_')}.json"
rows = json.loads(path.read_text(encoding="utf-8"))

shown = 0
for r in rows:
    if r["reason"] != "llm_said_no":
        continue
    shown += 1
    print(f"\n[{shown}] {r['title']}")
    print("  experts labelled:", (r["gold_text"] or ["?"])[0].replace("\n", " ")[:350])
print(f"\n{shown} cases where the clause was shown but the model said not found.")
