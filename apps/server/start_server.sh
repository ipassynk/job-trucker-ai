#!/bin/bash
cd "$(dirname "$0")"
# Add project root to PYTHONPATH
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
