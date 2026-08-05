#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Checking Docker"
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Install Docker Desktop (or the Docker Engine) before running this script: https://docs.docker.com/get-docker/" >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker is installed but not running. Start Docker and re-run this script." >&2
  exit 1
fi

echo "==> Backend: virtual environment + dependencies"
cd "$REPO_ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
deactivate

echo "==> Frontend: npm install"
cd "$REPO_ROOT/frontend"
npm install

echo "==> Local environment file"
cd "$REPO_ROOT"
if [ ! -f "$REPO_ROOT/.env" ]; then
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  echo "Created .env from .env.example"
else
  echo ".env already exists — leaving it untouched"
fi

echo "==> Starting local database"
docker compose up -d

echo
echo "Setup complete. See README.md to start the backend and frontend."
