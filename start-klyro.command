#!/bin/bash
cd "$(dirname "$0")/backend"

echo "=== Killing any process on port 8000 ==="
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 1

echo "=== Installing dependencies ==="
pip3 install -r requirements.txt --quiet 2>&1

echo "=== Starting Klyro server on http://localhost:8000 ==="
export PATH="$HOME/.local/bin:$PATH"
python3 -m uvicorn app.factory:create_app --factory --host 0.0.0.0 --port 8000 --reload
