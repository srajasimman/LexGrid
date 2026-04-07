# LexGrid Makefile
# Common development commands for the LexGrid Legal RAG system

.PHONY: help up down build logs clean test lint ingest

# Default target
help:
	@echo "LexGrid — Available commands:"
	@echo ""
	@echo "  make up         - Start all services (docker compose)"
	@echo "  make down       - Stop all services"
	@echo "  make build      - Build all services"
	@echo "  make rebuild    - Rebuild all services (no cache)"
	@echo "  make logs       - View logs (all services)"
	@echo "  make logs-f     - Follow logs in real-time"
	@echo "  make ps         - Show running containers"
	@echo "  make clean      - Remove containers, networks, volumes"
	@echo ""
	@echo "  make backend-logs  - View backend logs"
	@echo "  make ui-logs       - View UI logs"
	@echo "  make postgres-logs - View postgres logs"
	@echo "  make redis-logs    - View redis logs"
	@echo ""
	@echo "  make health        - Check all services health"
	@echo "  make test          - Run backend tests"
	@echo "  make lint          - Run linters"
	@echo "  make ingest        - Run ingestion script (requires services running)"
	@echo ""

# Docker Compose commands
up:
	cd infra && docker compose up -d
	@echo "Services started. UI: http://localhost:3000 | Backend: http://localhost:8000"

down:
	cd infra && docker compose down

build:
	cd infra && docker compose build

rebuild:
	cd infra && docker compose build --no-cache

logs:
	cd infra && docker compose logs --tail=50

logs-f:
	cd infra && docker compose logs -f

ps:
	cd infra && docker compose ps

clean:
	cd infra && docker compose down -v --remove-orphans
	@echo "Cleaned up containers, networks, and volumes"

# Individual service logs
backend-logs:
	docker compose -f infra/docker-compose.yml logs --tail=100 backend

ui-logs:
	docker compose -f infra/docker-compose.yml logs --tail=100 ui

postgres-logs:
	docker compose -f infra/docker-compose.yml logs --tail=100 postgres

redis-logs:
	docker compose -f infra/docker-compose.yml logs --tail=100 redis

# Health check
health:
	@echo "Checking service health..."
	@echo -n "Postgres: "; curl -sf http://localhost:8000/health 2>/dev/null | grep -q "postgres" && echo "OK" || echo "CHECK"
	@echo -n "Backend: "; curl -sf http://localhost:8000/health >/dev/null && echo "OK" || echo "DOWN"
	@echo -n "UI:      "; curl -sf http://localhost:3000 >/dev/null && echo "OK" || echo "DOWN"

# Run tests (requires services up)
test:
	cd backend && .venv/bin/pytest -v || uv run pytest -v

# Run linters
lint:
	cd backend && .venv/bin/ruff check . || uv run ruff check .

# Run ingestion (requires services up)
ingest:
	cd .. && python scripts/ingest.py

# Database helpers
db-reset:
	docker compose -f infra/docker-compose.yml exec postgres psql -U lexgrid -d lexgrid -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

db-migrate:
	cd backend && alembic upgrade head

purge-cache:
	./scripts/purge_cache.sh --docker --all
