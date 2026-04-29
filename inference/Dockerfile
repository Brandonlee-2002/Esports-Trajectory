# ── Esports Career Inference Service ─────────────────────────────────────────
# Deploys to Google Cloud Run via:
#   gcloud run deploy esports-inference --source .
FROM python:3.12-slim

LABEL maintainer="Brandon Lee & Stephani Marie Soriano"
LABEL service="esports-career-inference"
LABEL description="REST API serving LoL career longevity predictions (Cox PH + Negative Binomial)"

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python deps — install before copying code so Docker caches this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy trained model files
COPY models/ ./models/

# Copy Flask app
COPY app.py .

# Cloud Run sets PORT env var; default to 8080
ENV PORT=8080
ENV MODEL_DIR=/app/models

EXPOSE 8080

# Use gunicorn for production (handles concurrent requests)
CMD exec gunicorn \
        --bind 0.0.0.0:$PORT \
        --workers 2 \
        --threads 4 \
        --timeout 60 \
        app:app