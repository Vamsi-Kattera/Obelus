Results on the test split (presence = is the clause there; span = does the quote match the experts' text)

| Clause | With / without | Method | Presence P | Presence R | Presence F1 | Span P | Span R | Span F1 |
|---|---|---|---|---|---|---|---|---|
| Cap On Liability | 56 / 46 | 1. BM25 | 93% | 89% | 91% | 42% | 50% | 46% |
| Cap On Liability | 56 / 46 | 2. BM25 + LLM | 80% | 93% | 86% | 82% | 62% | 71% |
| Cap On Liability | 56 / 46 | 3. BM25 gate + LLM | 98% | 82% | 89% | 82% | 58% | 68% |
| Termination For Convenience | 34 / 68 | 1. BM25 | 41% | 94% | 57% | 14% | 54% | 22% |
| Termination For Convenience | 34 / 68 | 2. BM25 + LLM | 84% | 91% | 87% | 79% | 72% | 75% |
| Termination For Convenience | 34 / 68 | 3. BM25 gate + LLM | 88% | 85% | 87% | 78% | 69% | 73% |
| Audit Rights | 50 / 52 | 1. BM25 | 93% | 76% | 84% | 39% | 48% | 43% |
| Audit Rights | 50 / 52 | 2. BM25 + LLM | 92% | 92% | 92% | 62% | 56% | 59% |
| Audit Rights | 50 / 52 | 3. BM25 gate + LLM | 97% | 72% | 83% | 60% | 48% | 53% |
| Anti-Assignment | 80 / 22 | 1. BM25 | 96% | 90% | 93% | 30% | 57% | 39% |
| Anti-Assignment | 80 / 22 | 2. BM25 + LLM | 99% | 96% | 97% | 65% | 72% | 68% |
| Anti-Assignment | 80 / 22 | 3. BM25 gate + LLM | 100% | 88% | 93% | 65% | 68% | 67% |