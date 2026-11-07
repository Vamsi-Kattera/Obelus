Results on the dev split (presence = is the clause there; span = does the quote match the experts' text)

| Clause | With / without | Method | Presence P | Presence R | Presence F1 | Span P | Span R | Span F1 |
|---|---|---|---|---|---|---|---|---|
| Cap On Liability | 60 / 42 | 1. BM25 | 96% | 90% | 93% | 43% | 51% | 47% |
| Cap On Liability | 60 / 42 | 2. BM25 + LLM | 83% | 95% | 88% | 75% | 61% | 67% |
| Cap On Liability | 60 / 42 | 3. BM25 gate + LLM | 98% | 87% | 92% | 74% | 57% | 65% |