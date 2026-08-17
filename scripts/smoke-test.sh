#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

binding_to_origin() {
  local binding="$1"
  local host="${binding%:*}"
  local port="${binding##*:}"

  if [[ "$host" == \[*\] ]]; then
    host="${host:1:${#host}-2}"
  fi
  if [[ "$host" == "0.0.0.0" || "$host" == "::" ]]; then
    host="127.0.0.1"
  elif [[ "$host" == *:* ]]; then
    host="[$host]"
  fi

  printf 'http://%s:%s' "$host" "$port"
}

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

echo "Building and starting stack..."
docker compose up --build -d

backend_binding="$(docker compose port backend 8000)"
frontend_binding="$(docker compose port frontend 3000)"
BACKEND_ORIGIN="$(binding_to_origin "$backend_binding")"
FRONTEND_ORIGIN="$(binding_to_origin "$frontend_binding")"

echo "Waiting for backend health..."
for _ in $(seq 1 60); do
  if curl -fsS "$BACKEND_ORIGIN/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

curl -fsS "$BACKEND_ORIGIN/health/live" | tee /tmp/hushmap-live.json
curl -fsS "$BACKEND_ORIGIN/health/ready" | tee /tmp/hushmap-ready.json
curl -fsS "$BACKEND_ORIGIN/" | tee /tmp/hushmap-root.json
curl -fsS "$BACKEND_ORIGIN/geojson/points" | tee /tmp/hushmap-points.json

echo "Waiting for frontend..."
for _ in $(seq 1 60); do
  if curl -fsS "$FRONTEND_ORIGIN/" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

curl -fsS -o /dev/null -w "frontend:%{http_code}\n" "$FRONTEND_ORIGIN/"

echo "Waiting for frontend container health..."
frontend_container="$(docker compose ps -q frontend)"
frontend_health=""
for _ in $(seq 1 30); do
  frontend_health="$(docker inspect --format '{{.State.Health.Status}}' "$frontend_container" 2>/dev/null || true)"
  if [[ "$frontend_health" == "healthy" ]]; then
    break
  fi
  sleep 2
done

if [[ "$frontend_health" != "healthy" ]]; then
  echo "Frontend container did not become healthy (status: ${frontend_health:-unknown})." >&2
  docker compose ps
  exit 1
fi

echo "Smoke test passed."
