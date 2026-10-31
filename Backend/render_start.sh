#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
python -m alembic upgrade head
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
