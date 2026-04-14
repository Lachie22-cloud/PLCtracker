#!/usr/bin/env bash
# Local dev runner
set -e
export PORT="${PORT:-8000}"
export PLCT_DB_PATH="${PLCT_DB_PATH:-$(pwd)/data/app.db}"
mkdir -p "$(dirname "$PLCT_DB_PATH")"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
