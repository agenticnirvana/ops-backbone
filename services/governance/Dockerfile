FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
  && rm -rf /var/lib/apt/lists/*

COPY services/governance/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY platform/shared /app/shared
COPY services/governance/main.py .

ENV PYTHONPATH=/app
EXPOSE 8093

HEALTHCHECK --interval=10s --timeout=5s --retries=8 --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8093/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8093"]
