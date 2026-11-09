# Build from the repository root:  docker build -f apps/api/Dockerfile -t touchline-api .
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 HF_HUB_DISABLE_SYMLINKS_WARNING=1
# the code expects the repo layout: /app/apps/api (code) and /app/data (knowledge + sample list)
WORKDIR /app/apps/api

COPY apps/api/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY apps/api/ ./
COPY data/knowledge /app/data/knowledge
COPY data/samples /app/data/samples

# Bake the ~65 MB embedding model into the image so the first request is not slow.
RUN python -c "from app.services.embeddings import _model; _model()"

RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000
# bootstrap: wait for the database, migrate, load data and build the index if missing (idempotent), then serve.
CMD ["sh", "-c", "python -m app.services.bootstrap && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
