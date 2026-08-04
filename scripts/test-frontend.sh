#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Frontend unit tests (vitest)"
cd "$REPO_ROOT/frontend"
npx vitest run
