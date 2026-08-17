#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

echo "Building and starting stack..."
docker compose up --build -d

echo "Waiting for backend health..."
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/health/live >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

curl -fsS http://127.0.0.1:8000/health/live | tee /tmp/hushmap-live.json
curl -fsS http://127.0.0.1:8000/health/ready | tee /tmp/hushmap-ready.json
curl -fsS http://127.0.0.1:8000/ | tee /tmp/hushmap-root.json

echo "Waiting for frontend..."
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:3000/ >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

curl -fsS -o /dev/null -w "frontend:%{http_code}\n" http://127.0.0.1:3000/

echo "Smoke test passed."
