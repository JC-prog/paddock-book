#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Backend unit tests (pytest)"
cd "$REPO_ROOT/backend"
source .venv/bin/activate
pytest --cov --cov-report=term-missing --cov-report=xml tests/unit
