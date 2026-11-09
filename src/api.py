"""Obelus HTTP API.

Run locally from C:\\dev\\clauselens:
    uvicorn api:app --app-dir src --port 8080
Environment:
    GEMINI_API_KEY        required (set in your own terminal, never in a file)
    CLAUSELENS_API_TOKEN  optional; if set, requests must send header  X-API-Key: <token>
    CLAUSELENS_MODEL      optional model name
    OBELUS_DEMO           set to 1 for the public demo: smaller inputs, per-visitor and daily limits
Privacy: contract text is sent to Google's Gemini API. Do not upload confidential contracts.
"""
import hmac
import logging
import os
from typing import Optional

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from limits import DemoLimiter, RateLimited
from llm import MODEL, DailyQuotaError, gemini_json
from service import (DISCLAIMER, EVALUATED, MAX_CHARS, MAX_CLAUSES, SUPPORTED, AnalyzeRequest, AnalyzeResponse,
                     UnknownClause, analyze)

DEMO_MAX_CHARS = 60_000     # about 20 pages: keeps each demo call small
DEMO_MAX_CLAUSES = 3
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
limiter = DemoLimiter(per_visitor=5, window_s=3600, daily_cap=100)

log = logging.getLogger("obelus")
logging.basicConfig(level=logging.INFO, format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}')

if not os.environ.get("GEMINI_API_KEY"):
    log.warning("GEMINI_API_KEY is not set: /analyze will fail until it is provided")

app = FastAPI(title="Obelus", version="0.1.0", description=DISCLAIMER)


def get_llm():
    return gemini_json


def demo_on() -> bool:
    return os.environ.get("OBELUS_DEMO") == "1"


def visitor_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_token(x_api_key: Optional[str] = Header(default=None)):
    expected = os.environ.get("CLAUSELENS_API_TOKEN")
    if expected and not hmac.compare_digest(x_api_key or "", expected):
        raise HTTPException(status_code=401, detail="missing or wrong X-API-Key")


@app.get("/health")
def health():
    demo = demo_on()
    return {"status": "ok", "model": MODEL, "key_configured": bool(os.environ.get("GEMINI_API_KEY")),
            "demo": demo, "max_chars": DEMO_MAX_CHARS if demo else MAX_CHARS,
            "max_clauses": DEMO_MAX_CLAUSES if demo else MAX_CLAUSES}


@app.get("/", include_in_schema=False)
def home():
    page = WEB_DIR / "index.html"
    if page.exists():
        return FileResponse(page)
    return JSONResponse({"name": "Obelus", "docs": "/docs"})


@app.get("/clauses")
def clauses():
    return {"measured": EVALUATED, "supported": SUPPORTED}


@app.post("/analyze", response_model=AnalyzeResponse, dependencies=[Depends(check_token)])
def analyze_contract(req: AnalyzeRequest, request: Request, llm=Depends(get_llm)):
    if demo_on():
        if len(req.text) > DEMO_MAX_CHARS:
            raise HTTPException(status_code=413, detail=f"The demo accepts up to {DEMO_MAX_CHARS:,} characters "
                                                        "(about 20 pages). Paste a shorter extract.")
        if not req.clauses or len(req.clauses) > DEMO_MAX_CLAUSES:
            raise HTTPException(status_code=422, detail=f"Choose between 1 and {DEMO_MAX_CLAUSES} clauses.")
        try:
            limiter.check(visitor_id(request))
        except RateLimited as exc:
            raise HTTPException(status_code=429, detail=exc.message,
                                headers={"Retry-After": str(exc.retry_after)})
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