FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/

WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1
ENV FRONTEND_STATIC_DIR=../frontend/static
ENV FRONTEND_TEMPLATES_DIR=../frontend/templates

EXPOSE 8000

CMD uvicorn app.factory:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 2
