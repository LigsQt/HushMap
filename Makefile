.PHONY: setup up down logs dev db-start db-stop db-reset db-migrate db-seed test lint fmt backend-sync frontend-sync smoke

setup:
	cp -n .env.example .env || true
	cd backend && uv sync
	cd frontend && pnpm install --frozen-lockfile

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

dev:
	docker compose -f compose.yaml -f compose.dev.yaml up --build

db-start:
	docker compose up -d postgres

db-stop:
	docker compose stop postgres

db-reset:
	docker compose down -v
	docker compose up -d postgres
	docker compose run --rm migrate
	$(MAKE) db-seed

db-migrate:
	docker compose run --rm migrate

db-seed:
	docker compose exec -T postgres psql -U $${POSTGRES_USER:-hushmap} -d $${POSTGRES_DB:-hushmap} < backend/migrations/seed.sql

backend-sync:
	cd backend && uv sync --frozen

frontend-sync:
	cd frontend && pnpm install --frozen-lockfile

test:
	cd backend && uv run pytest
	cd frontend && pnpm check

lint:
	cd backend && uv run ruff check .
	cd frontend && pnpm lint

fmt:
	cd backend && uv run ruff check --fix .
	cd frontend && pnpm fmt:fix

smoke:
	./scripts/smoke-test.sh
