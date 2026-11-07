"""ClauseLens step 1: look at the data before building anything."""
import json
from collections import Counter
from pathlib import Path

path = next(Path("data").rglob("CUAD_v1.json"))
data = json.loads(path.read_text(encoding="utf-8"))["data"]

print(f"Contracts: {len(data)}")

found = Counter()
total = Counter()
lengths = []

for contract in data:
    para = contract["paragraphs"][0]
    lengths.append(len(para["context"]))
    for qa in para["qas"]:
        clause = qa["id"].split("__")[-1]
        total[clause] += 1
        if qa["answers"]:
            found[clause] += 1

print(f"Clause types: {len(total)}")
print(f"Average contract length: {sum(lengths)//len(lengths):,} characters\n")
print(f"{'Clause type':45} {'present in':>10}")
for clause, n in found.most_common():
    print(f"{clause:45} {n:>4}/{total[clause]} ({n/total[clause]:.0%})")

c = data[0]
qa = next(q for q in c["paragraphs"][0]["qas"] if q["answers"])
print("\nExample contract:", c["title"])
print("Clause:", qa["id"].split("__")[-1])
print("Labelled text:", qa["answers"][0]["text"][:300])
