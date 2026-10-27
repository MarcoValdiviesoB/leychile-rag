# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY requirements.txt pyproject.toml ./
COPY src ./src
COPY data ./data
RUN pip install -r requirements.txt && pip install -e .

EXPOSE 8000
# La app consulta la DB (Neon) vía DATABASE_URL y usa OPENAI_API_KEY (bring-your-own-key).
# Para poblar el corpus una vez: `docker run --rm -e ... IMG python scripts/run_ingest.py seed`
COPY scripts ./scripts
CMD ["sh", "-c", "uvicorn leychile_rag.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
