# LexGrid - Coding Agent Instructions

This file provides guidance to Coding Agents working on this project. It includes an overview of the system, architectural details, commands for development and deployment, and conventions to follow when contributing code.

## Project Overview

LexGrid is a production-grade RAG (Retrieval-Augmented Generation) system for querying 9 Indian Bare Acts (BNS, CPC, CrPC, HMA, IDA, IEA, IPC, MVA, NIA). It combines hybrid retrieval (vector + full-text search with RRF fusion) with an anti-hallucination LLM layer to provide cited, accurate legal answers.

## Documentation

Detailed documentation is available in the `docs/` directory:

- [API Reference](./docs/api-reference.md) — Detailed docs for all backend API endpoints
- [Architecture Deep Dive](./docs/architecture.md) — In-depth explanation of the system architecture and design decisions
- [Ingestion Pipeline](./docs/ingestion.md) — How legal acts are ingested, processed, and stored in the database
- [Evaluation Framework](./docs/evaluation.md) — Test cases, evaluation metrics, and how to run evaluations
- [Developer Guide](./docs/developer-guide.md) — Coding conventions, environment setup, and contribution guidelines

## Commands

All primary commands are in the `Makefile`. Services run via Docker Compose (`infra/docker-compose.yml`).

```bash
# Start/stop
make up              # Start all services
make down            # Stop all services
make rebuild         # Rebuild images without cache

# Development
make ingest          # Run ingestion pipeline (requires services running)
make test            # Run test suite
make lint            # ruff + mypy
make health          # Check all service statuses

# Database
make db-reset        # Drop and recreate schema
make db-migrate      # Run Alembic migrations
make purge-cache     # Flush Redis cache (or: make purge-cache docker=true)

# Logs
make logs-f          # Follow all service logs
make backend-logs    # Backend only
```

Running tests directly inside the container:
```bash
docker exec lexgrid-backend pytest backend/tests/ -v
docker exec lexgrid-backend pytest backend/tests/ --cov=app --cov-report=term-missing
```

Linting (from `backend/`):
```bash
ruff check .                # Check
ruff check . --fix          # Auto-fix
mypy backend/               # Type checking
```

Local development without Docker (run postgres+redis in Docker, backend natively):
```bash
cd backend && python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
celery -A app.workers.celery_app worker --loglevel=info  # in separate terminal
cd ui && npm install && npm run dev
```

## Architecture

### Infrastructure (5 containers)
- **postgres** (pgvector/pgvector:pg16) — sections table with embeddings (IVFFlat), tsvector FTS (GIN), and query_logs
- **redis** — DB0: query cache (TTL 3600s), DB1: Celery broker, DB2: Celery results
- **backend** — FastAPI + Uvicorn, all I/O async
- **celery-worker** — Same Docker image, runs batch ingestion tasks
- **ui** — Next.js 14 (App Router), React Query, TailwindCSS

### Full Query Pipeline (`backend/app/api/routes/query.py`)
1. **Query intelligence** (`retrieval/query_intelligence.py`) — regex detects "Section 302 IPC" patterns → direct DB lookup, sub-10ms, bypasses all LLM calls
2. **Cache check** (`cache/query_cache.py`) — SHA256-keyed Redis cache
3. **Embed query** (`embeddings/client.py`) — OpenAI `text-embedding-3-small` (1536-dim)
4. **Hybrid retrieve** (`retrieval/hybrid.py`) — RRF fusion (k=60) of:
   - Vector search: pgvector IVFFlat, cosine distance < 0.75
   - Full-text search: PostgreSQL tsvector/GIN
5. **Short-circuit** — if both retrievers return empty, return refusal without calling LLM
6. **Rerank** (`retrieval/reranker.py`) — gpt-4o-mini reranking
7. **Generate** (`llm/`) — gpt-4o-mini, temperature=0, 5-rule anti-hallucination system prompt, 4000-token context budget (tiktoken)
8. **Cache write + query logging**

### Key Design Rules
- **All I/O is async** (asyncpg, aioredis, httpx). Never block the event loop. Celery tasks bridge via `asyncio.run()`.
- **pydantic-settings** for all config — no hardcoded values, everything from environment
- **structlog** for all logging — never `print()` or `logging.getLogger()`
- **Mandatory citations** — every answer includes `[Section X, Act Name]` format
- LLM is OpenAI SDK pointed at OpenRouter (`OPENAI_BASE_URL=https://openrouter.ai/api/v1`)

### Code Conventions
- Ruff: line-length=100, target Python 3.11, rules E/F/I/UP
- mypy: strict=false, ignore_missing_imports=true
- pytest: asyncio_mode=auto (no `@pytest.mark.asyncio` needed)
- Tests are integration tests hitting real DB/Redis — do not mock the database

## Environment Variables

Minimum required in `.env`:
```
OPENAI_API_KEY=sk-or-v1-...        # OpenRouter key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
DATABASE_URL=postgresql+asyncpg://lexgrid:lexgrid@lexgrid-postgres:5432/lexgrid
REDIS_URL=redis://lexgrid-redis:6379/0
CELERY_BROKER_URL=redis://lexgrid-redis:6379/1
CELERY_RESULT_BACKEND=redis://lexgrid-redis:6379/2
```

See `.env.example` for full reference including model names and pipeline parameters.

## Legal Data

9 acts in `legal-acts/` directory (JSON format). Adding a new act: create JSON in `legal-acts/<act_code>/`, add act metadata to `backend/app/ingestion/loader.py`, then run `make ingest`.

Evaluation suite: 12 test cases in `backend/app/evaluation/test_cases.py` — run via `docker exec lexgrid-backend python scripts/evaluate.py`.
