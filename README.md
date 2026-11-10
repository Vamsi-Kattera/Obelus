# Obelus

[![CI](https://github.com/Vamsi-Kattera/Obelus/actions/workflows/ci.yml/badge.svg)](https://github.com/Vamsi-Kattera/Obelus/actions/workflows/ci.yml)

**Contract review that marks the passages worth a second look, and shows its evidence.**

**Live demo: https://huggingface.co/spaces/VamsiKattera/obelus** (paste a public contract extract or load a sample; a few analyses per visitor per hour)

An *obelus* is the mark scribes put beside a doubtful line. Obelus does the same for contracts: it finds clauses such as liability caps and termination rights, quotes the **exact text** with its position, and says "not found" when it has no evidence. It assists a human reviewer. It is **not legal advice**.

## Result in one line

On 102 held-out contracts it had never been tuned on, quoting with an LLM matched **59% to 75%** of the experts' labelled text on four clause types, up from **22% to 46%** for a keyword-search baseline. One number got worse, and it is reported below.

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

Temporary API errors are retried with exponential backoff; a used-up daily quota stops cleanly (HTTP 503) and results are cached on disk so a rerun costs nothing.

## Results

Measured on [CUAD](https://www.atticusprojectai.org/cuad) (510 real commercial contracts, expert-labelled). Contracts are split by contract (60% train, 20% dev, 20% test, fixed seed), so the system is never scored on contracts it was tuned on.

*Presence F1*: did it correctly say the clause is there or not? *Span F1*: how much of the experts' labelled text does the quote cover?

**Held-out test split (102 contracts, run once after all tuning was finished).**

| Clause | Contracts with / without | Presence F1: BM25 → Obelus | Span F1: BM25 → Obelus |
|---|---|---|---|
| Cap On Liability | 56 / 46 | 91% → 86% | 46% → 71% |
| Termination For Convenience | 34 / 68 | 57% → 87% | 22% → 75% |
| Audit Rights | 50 / 52 | 84% → 92% | 43% → 59% |
| Anti-Assignment | 80 / 22 | 93% → 97% | 39% → 68% |

**Dev split (102 contracts)**, used while building:

| Clause | Contracts with / without | Presence F1: BM25 → Obelus | Span F1: BM25 → Obelus |
|---|---|---|---|
| Cap On Liability | 60 / 42 | 93% → 88% | 47% → 67% |
| Termination For Convenience | 36 / 66 | 59% → 90% | 25% → 60% |
| Audit Rights | 46 / 56 | 87% → 95% | 41% → 63% |
| Anti-Assignment | 74 / 28 | 91% → 97% | 42% → 73% |

The test results match the dev results, so the gains are not an artefact of tuning. Per-method tables for the test split are in [`eval/results.md`](eval/results.md).

How to read it honestly:

- **Quotes got much better; the yes/no on liability caps got worse.** On Cap On Liability, presence F1 fell from 91% to 86% (93% to 88% on dev) because the LLM flags a limit in more contracts than the experts did (precision 80%). That is why the output is a highlighted passage for a person to read, not an automatic verdict.
- **Absolute accuracy is moderate.** A span F1 of 59% to 75% helps a reviewer who reads the highlight. It is not good enough to trust unreviewed.
- **A gated variant** (call the LLM only when the BM25 score is high enough) was not better than the default on either split, so it is not the default.
- **Only Cap On Liability was tuned on dev data**; the other three clause descriptions were written before seeing any results. The test split was not touched until the end.
- **Samples are small** (34 to 80 contracts with each clause), so differences of a few points are noise. Differences of 20 points or more are not.

## What I learned

- **My first prompt failed on Cap On Liability, and the model was not the problem.** Recall was 31%. Sorting each miss into retrieval / model refused / quote not found showed that the experts' label also covers *exclusions of consequential damages*, which my description left out. Fixing the definition took span F1 on 30 contracts from 28% to 79%.
- **The 30-contract number was optimistic.** On all 102 dev contracts it settled at about 70%. I quote the larger sample.
- **A plain keyword baseline is hard to beat on "is it there?"**: on Cap On Liability BM25 beat the LLM on presence on both splits. The LLM wins on pinpointing the text, and by a wide margin on clauses where BM25 over-flags (Termination For Convenience, dev: precision 43% → 91%).
- **A free tier is a design constraint.** The daily quota ended my first full run. A clean stop on quota errors, a disk cache that makes reruns free, and limits on the public demo came from that.
- **Keep the test set for the end.** Run it once, after the last change, and report what it says.

## Public demo

The live demo runs the same code with `OBELUS_DEMO=1`: at most 60,000 characters and 3 clauses per request, 5 analyses per visitor per hour and 100 per day overall. The Gemini key is a Space secret and is never in this repository. Logs record sizes and timing, never contract text.

## Limitations

- Only four clauses have measured accuracy; others are supported but marked `measured: false`.
- Quotes sometimes cover part of a provision (test span recall is about 56% to 72%).
- Contract text is sent to Google's Gemini API. **Do not upload confidential contracts.**
- English commercial contracts only. No OCR: PDFs must already have a text layer.

## Run it

```powershell
pip install -r requirements-dev.txt
python -m pytest tests -q
$env:GEMINI_API_KEY = "your-key"     # set in your own terminal; never commit it
uvicorn api:app --app-dir src --port 8080
```

Then open http://localhost:8080 for the web page, or use the API below. Set `OBELUS_DEMO=1` to switch on the demo limits.

Docker:

```powershell
docker build -t obelus .
docker run --rm -e GEMINI_API_KEY=$env:GEMINI_API_KEY -p 8080:8080 obelus
```

Endpoints: `GET /` (web page), `GET /health`, `GET /clauses`, `POST /analyze` (interactive docs at `/docs`). Optional header `X-API-Key` when `CLAUSELENS_API_TOKEN` is set.

## Data and credit

Contract data and labels: **CUAD**, The Atticus Project (Hendrycks et al., 2021), licensed CC BY 4.0. The dataset is not included in this repository.