"""Print the Gemini models your key can use for generateContent.

Run from C:\\dev\\clauselens (key set in your own terminal first):
    python src\\list_models.py
"""
import os

from google import genai
from google.genai import types

for version in ("v1beta", "v1"):
    print(f"\n--- API version {version} ---")
    try:
        client = genai.Client(http_options=types.HttpOptions(api_version=version))
        for m in client.models.list():
            actions = getattr(m, "supported_actions", None) or []
            if "generateContent" in actions and "flash" in m.name:
                print(m.name)
    except Exception as exc:                       # noqa: BLE001
        print("error:", str(exc)[:200])
