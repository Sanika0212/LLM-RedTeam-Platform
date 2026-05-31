FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY backend/ .
COPY redteam-engine/ ./redteam-engine/
COPY workers/ ./workers/

CMD ["celery", "-A", "workers.eval_worker", "worker", "--loglevel=info", "--concurrency=4"]
