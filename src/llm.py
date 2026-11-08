"""Thin Gemini wrapper: structured output, retries with backoff, no key handling in code.

The key is read from the GEMINI_API_KEY environment variable. Never paste it into a file.
Set it in your own terminal for this session only:
    $env:GEMINI_API_KEY = "your-key"
"""
import hashlib
import json
import os
import random
import time
from pathlib import Path

# Override without editing code:  $env:CLAUSELENS_MODEL = "model-name"
def env_or_default(name, default):
    """Read an environment variable, treating an empty value the same as 'not set'."""
    return (os.environ.get(name) or "").strip() or default


MODEL = env_or_default("CLAUSELENS_MODEL", "gemini-3.5-flash-lite")
API_VERSION = env_or_default("CLAUSELENS_API_VERSION", "v1beta")
RETRY_WORDS = ("429", "500", "503", "unavailable", "overloaded", "resource_exhausted", "timeout")


class DailyQuotaError(RuntimeError):
    """The free-tier daily request limit is used up. Waiting a few seconds will not help."""


def is_daily_quota(message):
    m = message.lower()
    return "perday" in m or "per day" in m or "requests per day" in m


def call_with_retries(fn, attempts=5, base=2.0, sleep=time.sleep):
    """Call fn(); on a temporary error wait base*2^n seconds (plus jitter) and try again."""
    for n in range(attempts):
        try:
            return fn()
        except Exception as exc:                      # noqa: BLE001
            if is_daily_quota(str(exc)):
                raise DailyQuotaError(
                    "Daily request limit reached for this model. Cached answers are kept; "
                    "rerun after the quota resets.") from exc
            temporary = any(w in str(exc).lower() for w in RETRY_WORDS)
            if not temporary or n == attempts - 1:
                raise
            sleep(base * (2 ** n) + random.uniform(0, 1))


def gemini_json(prompt, schema, model=MODEL):
    """Ask Gemini for JSON that matches a Pydantic model. Returns a plain dict."""
    from google import genai                         # imported here so tests need no SDK
    from google.genai import types

    client = genai.Client(http_options=types.HttpOptions(api_version=API_VERSION))  # key from GEMINI_API_KEY

    def once():
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0,
            ),
        )
        return schema.model_validate_json(resp.text).model_dump()

    return call_with_retries(once)


def cached(fn, path="eval/llm_cache.json"):
    """Wrap an LLM function so identical questions are answered from disk, not the API.
    The key covers the model, the schema name and the full prompt, so changing the
    prompt (or the model) automatically asks the model again."""
    file = Path(path)
    try:
        store = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
    except (OSError, ValueError):
        store = {}

    def wrapper(prompt, schema):
        key = hashlib.sha256(f"{MODEL}|{schema.__name__}|{prompt}".encode("utf-8")).hexdigest()
        if key in store:
            return store[key]
        result = fn(prompt, schema)
        store[key] = result
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(store), encoding="utf-8")
        return result

    return wrapper