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
# Set GEMINI_API_KEY for embedded AI. DEVICE_API_KEYS is optional in development.
docker compose up --build
```

Or use Make:

```bash
make setup
make up
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

## Security and data handling

- Report vulnerabilities according to [SECURITY.md](SECURITY.md); do not include secrets in public issues.
- `.env` files, database backups, and recovered data extracts are intentionally excluded from Git. Keep production credentials and source data in private storage.
- The committed database seed is sanitized development data. Deployments that collect audio or location data are responsible for obtaining consent and complying with applicable privacy requirements.
- Embedded AI analysis requires a Gemini API key supplied through the environment. Review the provider's terms and data-handling settings before enabling it for real recordings.

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

`make db-reset` destroys the local Docker volume and recreates schema + seed. Do not run it against shared environments.

## Host development (without full Compose app stack)

```bash
# Terminal 1
docker compose up -d postgres
cd backend && uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
cp ../.env.example .env   # set BACKEND_URL=http://127.0.0.1:8000
pnpm install --frozen-lockfile
pnpm dev
```

Hot-reload Compose variant:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

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
