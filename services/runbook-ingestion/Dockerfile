FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
  && rm -rf /var/lib/apt/lists/*

COPY agent/requirements.txt /tmp/agent-req.txt
COPY services/runbook-ingestion/requirements.txt /tmp/ingestion-req.txt
RUN pip install --no-cache-dir -r /tmp/agent-req.txt -r /tmp/ingestion-req.txt

COPY agent/rag /app/rag
COPY services/runbook-ingestion/app /app/app

ENV PYTHONPATH=/app
ENV CHROMA_PATH=/data/chroma
ENV RUNBOOKS_DIR=/data/runbooks
ENV SEED_RUNBOOKS_DIR=/seed/runbooks
ENV INDEX_MANIFEST_PATH=/data/chroma/active.json

EXPOSE 8092

HEALTHCHECK --interval=15s --timeout=5s --start-period=45s --retries=8 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8092/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8092"]
