#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

echo "Running backend tests..."
PYTHONPATH=backend/src .venv/bin/python -m pytest backend/tests

echo "Running frontend tests..."
cd frontend
npm run test
