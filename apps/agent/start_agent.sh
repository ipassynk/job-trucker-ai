#!/bin/bash
cd "$(dirname "$0")"
# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi
# Add project root to PYTHONPATH
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}"
python3 agent.py
