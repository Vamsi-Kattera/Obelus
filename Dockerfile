FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the service code and the web page go in the image: no CUAD data, no cache, no key.
COPY src/service.py src/api.py src/limits.py src/extract.py src/llm.py src/chunk.py src/baseline_bm25.py src/evaluate.py ./src/
COPY web ./web/

RUN useradd --create-home appuser
USER appuser

EXPOSE 8080
# Pass the key at run time:  docker run -e GEMINI_API_KEY=... -p 8080:8080 obelus
CMD ["uvicorn", "api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8080"]