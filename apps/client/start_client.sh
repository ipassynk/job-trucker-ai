#!/bin/bash
cd "$(dirname "$0")"
# Add project root to PYTHONPATH
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}"
streamlit run jobs_chat.py