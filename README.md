# Obelus

[![CI](https://github.com/Vamsi-Kattera/Obelus/actions/workflows/ci.yml/badge.svg)](https://github.com/Vamsi-Kattera/Obelus/actions/workflows/ci.yml)

**Contract review that marks the passages worth a second look, and shows its evidence.**

An *obelus* is the mark scribes put beside a doubtful line. Obelus does the same for contracts: it finds clauses such as liability caps and termination rights, quotes the **exact text** with its position, and says "not found" when it has no evidence. It assists a human reviewer. It is **not legal advice**.

## Example

```powershell
$body = @{ text = "In no event shall either party's liability exceed the fees paid in the prior twelve months."; clauses = @("Cap On Liability") } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8080/analyze -Body $body -ContentType "application/json"
```

```json
{ "clause": "Cap On Liability", "found": true,
  "passages": [{ "start": 0, "end": 91, "text": "In no event shall either party's liability exceed the fees paid in the prior twelve months." }],
  "measured": true }
```

## How it works

1. **Chunk** the contract into overlapping 1,200-character windows.
2. **Retrieve** the six chunks that best match the clause (BM25).
3. **Extract** with Gemini, which returns structured JSON (`found`, `quotes`) validated by Pydantic.
4. **Ground** every quote: it must exist in the original contract (whitespace-insensitive). A quote that does not is dropped, and if none survive the answer is "not found". Cite or abstain.

Temporary API errors are retried with exponential backoff; a used-up daily quota stops cleanly (HTTP 503).

## Results

Measured on [CUAD](https://www.atticusprojectai.org/cuad) (510 real commercial contracts, expert-labelled). Contracts are split by contract (60% train, 20% dev, 20% test, fixed seed), so the system is never scored on contracts it was tuned on.

**Dev split (102 contracts).** *Presence F1*: did it correctly say the clause is there or not? *Span F1*: how much of the experts' labelled text does the quote cover?

| Clause | Contracts with / without | Presence F1: BM25 → Obelus | Span F1: BM25 → Obelus |
|---|---|---|---|
| Cap On Liability | 60 / 42 | 93% → 88% | 47% → 67% |
| Termination For Convenience | 36 / 66 | 59% → 90% | 25% → 60% |
| Audit Rights | 46 / 56 | 87% → 95% | 41% → 63% |
| Anti-Assignment | 74 / 28 | 91% → 97% | 42% → 73% |

**Held-out test split:** TODO (run once, after all tuning is finished).

Only Cap On Liability was tuned on dev data; the other three used descriptions written before seeing any results. Full per-method tables are in [`eval/results.md`](eval/results.md). Samples are small (36 to 74 contracts with each clause), so differences of a few points are noise. Differences of 20 points or more are not.

## What I learned

- **My first prompt failed on Cap On Liability, and the model was not the problem.** Recall was 31%. Sorting each miss into retrieval / model refused / quote not found showed that the experts' label also covers *exclusions of consequential damages*, which my description left out. Fixing the definition took span F1 on 30 contracts from 28% to 79%.
- **The 30-contract number was optimistic.** On all 102 dev contracts it settled at about 70%. I quote the larger one.
- **A plain keyword baseline is hard to beat on "is it there?"**: BM25 beats the LLM on presence for Cap On Liability. The LLM wins on pinpointing the text, and by a wide margin on clauses where BM25 over-flags (Termination For Convenience: precision 43% → 91%).
- **Requiring a combined BM25 + LLM agreement** reduced false alarms but lowered recall, and was not better in three of four clauses, so it is not the default. For a review tool, missing a clause is worse than a false alarm.

## Limitations

- Only four clauses have measured accuracy; others are supported but marked `measured: false`.
- Quotes sometimes cover part of a provision (span recall is about 60 to 80%).
- Contract text is sent to Google's Gemini API. **Do not upload confidential contracts.**
- English commercial contracts only. No OCR: PDFs must already have a text layer.

## Run it

```powershell
pip install -r requirements-dev.txt
python -m pytest tests -q
$env:GEMINI_API_KEY = "your-key"     # set in your own terminal; never commit it
uvicorn api:app --app-dir src --port 8080
```

Docker:

```powershell
docker build -t obelus .
docker run --rm -e GEMINI_API_KEY=$env:GEMINI_API_KEY -p 8080:8080 obelus
```

Endpoints: `GET /health`, `GET /clauses`, `POST /analyze` (interactive docs at `/docs`). Optional header `X-API-Key` when `CLAUSELENS_API_TOKEN` is set.

## Data and credit

Contract data and labels: **CUAD**, The Atticus Project (Hendrycks et al., 2021), licensed CC BY 4.0. The dataset is not included in this repository.
