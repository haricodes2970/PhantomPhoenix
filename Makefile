.PHONY: help venv db migrate test test-db build run-backend run-frontend verify

help:
	@echo "PHANTOM PHOENIX - Local Development Commands"
	@echo "--------------------------------------------"
	@echo "make db           - Start PostgreSQL via Docker Compose"
	@echo "make migrate      - Run database migrations"
	@echo "make test         - Run unit & forensic tests (no GPU/model required)"
	@echo "make test-db      - Run PostgreSQL integration tests"
	@echo "make build        - Build frontend production bundle"
	@echo "make run-backend  - Start FastAPI backend server"
	@echo "make run-frontend - Start Vite frontend dev server"
	@echo "make verify       - Run all unit tests, DB integration tests, and build"

db:
	docker compose up -d
	@echo "Waiting for PostgreSQL health check..."
	@sleep 3
	docker compose ps

migrate:
	.venv/bin/python -m alembic upgrade head

test:
	.venv/bin/python -m pytest tests/ -v -k "not test_database and not test_real_model_smoke"

test-db:
	RUN_DB_TESTS=1 .venv/bin/python -m pytest tests/test_database.py -v

build:
	cd frontend && npm run build

run-backend:
	.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

run-frontend:
	cd frontend && npm run dev

verify: test test-db build
	@echo "All tests and frontend build verified successfully."
