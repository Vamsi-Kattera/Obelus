Results on the dev split (presence = is the clause there; span = does the quote match the experts' text)

| Clause | With / without | Method | Presence P | Presence R | Presence F1 | Span P | Span R | Span F1 |
|---|---|---|---|---|---|---|---|---|
| Cap On Liability | 60 / 42 | 1. BM25 | 96% | 90% | 93% | 43% | 51% | 47% |
| Cap On Liability | 60 / 42 | 2. BM25 + LLM | 83% | 95% | 88% | 75% | 61% | 67% |
| Cap On Liability | 60 / 42 | 3. BM25 gate + LLM | 98% | 87% | 92% | 74% | 57% | 65% |
| Termination For Convenience | 36 / 66 | 1. BM25 | 43% | 94% | 59% | 16% | 60% | 25% |
| Termination For Convenience | 36 / 66 | 2. BM25 + LLM | 91% | 89% | 90% | 56% | 66% | 60% |
| Termination For Convenience | 36 / 66 | 3. BM25 gate + LLM | 91% | 86% | 89% | 55% | 65% | 60% |
| Audit Rights | 46 / 56 | 1. BM25 | 93% | 83% | 87% | 41% | 41% | 41% |
| Audit Rights | 46 / 56 | 2. BM25 + LLM | 92% | 98% | 95% | 67% | 60% | 63% |
| Audit Rights | 46 / 56 | 3. BM25 gate + LLM | 97% | 83% | 89% | 67% | 56% | 61% |
| Anti-Assignment | 74 / 28 | 1. BM25 | 91% | 92% | 91% | 31% | 68% | 42% |
| Anti-Assignment | 74 / 28 | 2. BM25 + LLM | 96% | 97% | 97% | 66% | 81% | 73% |
| Anti-Assignment | 74 / 28 | 3. BM25 gate + LLM | 97% | 91% | 94% | 66% | 79% | 72% |