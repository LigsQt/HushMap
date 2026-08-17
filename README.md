# HushMap

Noise-mapping web application with a SvelteKit frontend, a FastAPI backend, PostgreSQL, and an embedded Gemini audio analysis provider.

## License

HushMap is released under the [MIT License](LICENSE).

## Architecture

```text
Browser -> SvelteKit (/api proxies) -> FastAPI -> PostgreSQL
                                     -> Gemini (embedded AI)
ESP32   -> FastAPI /upload/{session_id}
```

- `frontend/` — SvelteKit 2 + pnpm + `@sveltejs/adapter-node`
- `backend/` — FastAPI + uv + SQLAlchemy 2 + Alembic + Gemini provider

## Prerequisites

- Git
- Docker Engine or Docker Desktop with Docker Compose
- Optional for host development: [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/) 11, Node 22, Python 3.12

## First-time setup

```bash
cp .env.example .env
# GEMINI_API_KEY is optional unless AI analysis is needed.
docker compose up --build -d
./scripts/smoke-test.sh
```

The first run creates an empty database and a working empty map. To load the sanitized
sample point after the stack is healthy, run `make db-seed`.

Or use Make:

```bash
make setup
make up
make smoke
# Optional sanitized sample data:
make db-seed
```

## Service URLs

| Service | URL | Health |
| --- | --- | --- |
| Frontend | http://localhost:3000 | homepage |
| Backend | http://localhost:8000 | `/health/live`, `/health/ready` |
| PostgreSQL | localhost:15432 (Compose publish; override with `POSTGRES_PORT`) | Compose healthcheck |

Expected backend root response:

```json
{"message":"Working!"}
```

## Environment variables

See `.env.example`. Important values:

- `BACKEND_URL` — server-only SvelteKit → FastAPI URL (`http://backend:8000` in Docker, `http://127.0.0.1:8000` on the host)
- `DATABASE_URL` — SQLAlchemy psycopg URL
- `AI_MODE` — `embedded` (default) or `remote`
- `GEMINI_API_KEY` / `GEMINI_MODEL` — required for embedded AI
- `DEVICE_API_KEYS` — comma-separated upload keys; required outside development
- `ALLOW_UNAUTHENTICATED_DEVICE_UPLOADS` — explicit local bypass; honored only when `APP_ENV=development`
- `UPLOAD_RATE_LIMIT_PER_MINUTE` / `AUDIO_MAX_ACTIVE_SESSIONS_PER_DEVICE` — per-device ingestion limits
- `SUMMARY_RATE_LIMIT_PER_MINUTE` — per-client frontend summary limit
- `SUMMARY_REQUEST_RATE_LIMIT_PER_MINUTE` / `SUMMARY_GLOBAL_RATE_LIMIT_PER_MINUTE` — backend request and Gemini-call limits
- `HOST_BIND_ADDRESS` — Compose bind address; defaults to loopback
- `ADDRESS_HEADER` / `XFF_DEPTH` — adapter-node client-address settings for trusted reverse proxies only

## Security and data handling

- Report vulnerabilities according to [SECURITY.md](SECURITY.md); do not include secrets in public issues.
- `.env` files, database backups, and recovered data extracts are intentionally excluded from Git. Keep production credentials and source data in private storage.
- The committed database seed is sanitized development data. Deployments that collect audio or location data are responsible for obtaining consent and complying with applicable privacy requirements.
- Embedded AI analysis requires a Gemini API key supplied through the environment. Review the provider's terms and data-handling settings before enabling it for real recordings.
- The default Compose ports bind to `127.0.0.1`. Set `HOST_BIND_ADDRESS` deliberately if other hosts must connect.
- Production fails closed when device API keys are absent. The unauthenticated upload bypass requires both `APP_ENV=development` and `ALLOW_UNAUTHENTICATED_DEVICE_UPLOADS=true`.
- Session summaries remain a public read feature. The frontend limits each client, while the backend independently limits total requests and Gemini calls. Deployments with stricter access requirements should place the application behind their own user authentication.
- Behind a trusted reverse proxy, configure adapter-node's `ADDRESS_HEADER` and `XFF_DEPTH` so per-client limits use the browser address. The proxy must strip client-supplied forwarding headers before setting its own.

## Third-party services

The map uses Carto basemap styles through MapLibre. Embedded AI analysis uses the Google GenAI SDK when `AI_MODE=embedded`.

## Database migrations

Migrations run once through the Compose `migrate` service before the API starts:

```bash
docker compose run --rm migrate
# equivalent host command:
cd backend && uv run alembic upgrade head
```

Create a new migration after model changes:

```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

Load the sanitized seed:

```bash
make db-seed
```

The seed is optional. `/geojson/points` returns an empty GeoJSON feature collection
when no points exist, so the homepage and healthcheck remain valid on a clean database.

`make db-reset` destroys the local Docker volume and recreates schema + seed. Do not run it against shared environments.

## Host development (without full Compose app stack)

```bash
# Terminal 1
docker compose up -d postgres
cd backend
uv sync
export DATABASE_URL=postgresql+psycopg://hushmap:hushmap@127.0.0.1:15432/hushmap
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
cp .env.example .env
pnpm install --frozen-lockfile
pnpm dev
```

Hot-reload Compose variant:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

## Device uploads

`POST /upload/{session_id}` accepts raw 16 kHz, 32-bit, mono PCM chunks for an
existing session. Authenticate with `X-API-Key` or `Authorization: Bearer <key>`.
Optional `X-Chunk-Sequence` and `Idempotency-Key` headers provide ordering and
retry protection. Authentication, request-rate limits, session existence, and
header validity are checked before the request body is read. Body streaming is
size-limited, and per-device active-buffer quotas are enforced before AI
processing begins. Completed idempotency keys are retained for the configured
buffer TTL so a retried final chunk cannot trigger duplicate AI work. Configured
device keys currently grant upload access to all existing sessions.
If a new chunk arrives while the previous audio window is still being persisted,
the API returns `409 Conflict` with `Retry-After: 1`; clients must retry that
chunk rather than treating it as accepted.

## Common commands

```bash
make test
make lint
make logs
make down
./scripts/smoke-test.sh
```

Backend:

```bash
cd backend
uv sync --frozen
uv run pytest
uv run ruff check .
```

Frontend:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm check
pnpm lint
pnpm build
```

## Troubleshooting

- **Port already in use** — change `PORT` / `POSTGRES_PORT` in `.env`, or stop the conflicting process.
- **Unhealthy backend** — check `docker compose logs backend migrate postgres` and confirm `DATABASE_URL` points at `postgres` inside Compose.
- **Stale Docker volume** — `make db-reset` (destroys local data).
- **Missing env vars** — copy `.env.example` again and set `GEMINI_API_KEY` if AI routes are needed.
- **Lockfile mismatch** — use `uv sync --frozen` / `pnpm install --frozen-lockfile`; regenerate locks deliberately.
- **Apple Silicon image issues** — rebuild with `docker compose build --pull` and ensure the Docker engine supports `linux/arm64` wheels for NumPy/SciPy.
