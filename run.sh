#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export PYTHONPATH=src
echo "🚀 Starting MedIntel at http://127.0.0.1:8000 ..."
exec .venv/bin/uvicorn medintel_api.main:app --host 127.0.0.1 --port 8000 --reload
