"""Obelus HTTP API.

Run locally from C:\\dev\\clauselens:
    uvicorn api:app --app-dir src --port 8080
Environment:
    GEMINI_API_KEY        required (set in your own terminal, never in a file)
    CLAUSELENS_API_TOKEN  optional; if set, requests must send header  X-API-Key: <token>
    CLAUSELENS_MODEL      optional model name
Privacy: contract text is sent to Google's Gemini API. Do not upload confidential contracts.
"""
import hmac
import logging
import os
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException

from llm import MODEL, DailyQuotaError, gemini_json
from service import DISCLAIMER, EVALUATED, SUPPORTED, AnalyzeRequest, AnalyzeResponse, UnknownClause, analyze

log = logging.getLogger("obelus")
logging.basicConfig(level=logging.INFO, format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}')

if not os.environ.get("GEMINI_API_KEY"):
    log.warning("GEMINI_API_KEY is not set: /analyze will fail until it is provided")

app = FastAPI(title="Obelus", version="0.1.0", description=DISCLAIMER)


def get_llm():
    return gemini_json


def check_token(x_api_key: Optional[str] = Header(default=None)):
    expected = os.environ.get("CLAUSELENS_API_TOKEN")
    if expected and not hmac.compare_digest(x_api_key or "", expected):
        raise HTTPException(status_code=401, detail="missing or wrong X-API-Key")


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL, "key_configured": bool(os.environ.get("GEMINI_API_KEY"))}


@app.get("/clauses")
def clauses():
    return {"measured": EVALUATED, "supported": SUPPORTED}


@app.post("/analyze", response_model=AnalyzeResponse, dependencies=[Depends(check_token)])
def analyze_contract(req: AnalyzeRequest, llm=Depends(get_llm)):
    try:
        out = analyze(req, llm)
    except UnknownClause as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except DailyQuotaError:
        raise HTTPException(status_code=503, detail="model quota used up; try again later")
    except Exception:                                    # noqa: BLE001
        log.exception("analysis failed")                 # never log contract text
        raise HTTPException(status_code=502, detail="the model call failed")
    log.info("analyzed chars=%d clauses=%d elapsed_ms=%d", len(req.text), len(out.results), out.elapsed_ms)
    return out