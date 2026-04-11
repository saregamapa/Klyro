FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

WORKDIR /app/backend

# Create data directory for SQLite
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/database.db
ENV FRONTEND_STATIC_DIR=../frontend/static
ENV FRONTEND_TEMPLATES_DIR=../frontend/templates

EXPOSE 8000

CMD uvicorn app.factory:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 1
