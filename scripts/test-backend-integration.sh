#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO_ROOT"
if ! docker compose ps --status running --services 2>/dev/null | grep -qx "db"; then
  echo "The local database isn't running. Start it first: docker compose up -d" >&2
  exit 1
fi

echo "==> Backend integration tests (pytest, requires the local database)"
cd "$REPO_ROOT/backend"
source .venv/bin/activate
pytest tests/integration
