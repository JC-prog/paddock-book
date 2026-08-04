#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$REPO_ROOT/scripts/test-backend.sh"
echo
"$REPO_ROOT/scripts/test-frontend.sh"
echo
echo "All unit tests passed."
