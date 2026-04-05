# LexGrid Developer Guide

> This guide covers everything you need to develop, debug, and extend LexGrid — from local setup without Docker to adding new acts and endpoints.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Local Setup Without Docker](#2-local-setup-without-docker)
3. [Running the Backend](#3-running-the-backend)
4. [Running the Frontend](#4-running-the-frontend)
5. [Running with Docker Compose](#5-running-with-docker-compose)
6. [Environment Variables Reference](#6-environment-variables-reference)
7. [Code Conventions](#7-code-conventions)
8. [Project Structure](#8-project-structure)
9. [Running Tests](#9-running-tests)
10. [Linting & Type Checking](#10-linting--type-checking)
11. [How to Add a New Act](#11-how-to-add-a-new-act)
12. [How to Add a New API Endpoint](#12-how-to-add-a-new-api-endpoint)
13. [Debugging Tips](#13-debugging-tips)
14. [Common Pitfalls](#14-common-pitfalls)

---

## 1. Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | `pyenv install 3.11` |
| PostgreSQL | 16 | `brew install postgresql@16` |
| pgvector extension | latest | See note below |
| Redis | 7 | `brew install redis` |
| Node.js | 18+ | `nvm install 18` |

> **pgvector on macOS**: The easiest path is to use the Docker postgres container (`pgvector/pgvector:pg16`) even for local dev, and only run the backend natively. Alternatively, install from source: https://github.com/pgvector/pgvector#installation

---

## 2. Local Setup Without Docker

This path is faster for backend development — no container rebuild cycle. Run postgres and redis via Docker, backend natively.

### 2.1 Start PostgreSQL and Redis via Docker

```bash
cd infra

# Start only postgres and redis (not the full stack)
docker compose up -d postgres redis

# Verify they're healthy
docker compose ps
```

This gives you:
- PostgreSQL at `localhost:5432` (user: `lexgrid`, password: `lexgrid`, db: `lexgrid`)
- Redis at `localhost:6379`
- Schema is applied automatically from `infra/postgres/init.sql`

### 2.2 Python Environment

```bash
cd backend

# Create virtual environment (Python 3.11+)
python3.11 -m venv .venv
source .venv/bin/activate

# Install all dependencies including dev extras
pip install -e ".[dev]"
```

> **Why `-e .`?** Installs in editable mode so changes to `app/` are picked up immediately without reinstalling. The package name is `lexgrid-backend` (from `pyproject.toml`).

### 2.3 Environment File

```bash
# Copy the example (if it exists) or create from scratch
cp .env.example .env 2>/dev/null || touch .env
```

Minimum required variables for local dev:

```bash
# backend/.env
OPENAI_API_KEY=sk-...                    # Required — OpenAI or OpenRouter key
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional — override for OpenRouter

DATABASE_URL=postgresql+asyncpg://lexgrid:lexgrid@localhost:5432/lexgrid
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

LEGAL_ACTS_DIR=/path/to/LexGrid/legal-acts  # Absolute path to legal-acts/ dir
```

> **Using OpenRouter**: Set `OPENAI_BASE_URL=https://openrouter.ai/api/v1` and use your OpenRouter key as `OPENAI_API_KEY`. The OpenAI SDK is compatible with OpenRouter's API.

---

## 3. Running the Backend

```bash
cd backend
source .venv/bin/activate

# Development mode (auto-reload on file changes)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API root**: http://localhost:8000
- **Interactive docs (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Running the Celery Worker (for ingestion)

```bash
cd backend
source .venv/bin/activate

celery -A app.workers.celery_app worker \
    --loglevel=info \
    --concurrency=4
```

> **Note**: The `worker_prefetch_multiplier=1` is set in `celery_app.py` — each worker fetches one task at a time, preventing a single worker from hoarding all embed tasks.

---

## 4. Running the Frontend

```bash
cd ui
npm install
npm run dev
```

The UI will be available at http://localhost:3000. Configure the API URL:

```bash
# ui/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
BACKEND_URL=http://localhost:8000
```

---

## 5. Running with Docker Compose

```bash
# From the repo root
cd infra

# First time: build images
docker compose build

# Start all 5 services
docker compose up -d

# View logs for a specific service
docker compose logs -f backend
docker compose logs -f celery-worker

# Rebuild after backend code changes
docker compose up -d --build backend celery-worker

# Stop everything
docker compose down
```

### Container Health Check

```bash
docker compose ps
# All containers should show "Up (healthy)" or "Up"

# Check backend health directly
curl http://localhost:8000/health
# Expected: {"status":"ok","db":true,"redis":true,"openai":true}
```

---

## 6. Environment Variables Reference

All configuration is in `backend/app/config.py` using `pydantic-settings`. Values are read from environment variables or the `.env` file in the `backend/` directory.

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | OpenAI (or OpenRouter) API key |
| `OPENAI_BASE_URL` | ❌ | `https://api.openai.com/v1` | Override for OpenRouter or other compatible APIs |
| `DATABASE_URL` | ❌ | `postgresql+asyncpg://lexgrid:lexgrid@localhost:5432/lexgrid` | Async PostgreSQL URL |
| `REDIS_URL` | ❌ | `redis://localhost:6379/0` | Redis URL for query cache (db=0) |
| `CELERY_BROKER_URL` | ❌ | `redis://localhost:6379/1` | Celery broker (db=1) |
| `CELERY_RESULT_BACKEND` | ❌ | `redis://localhost:6379/2` | Celery results (db=2) |
| `EMBEDDING_MODEL` | ❌ | `text-embedding-3-small` | OpenAI embedding model |
| `LLM_MODEL` | ❌ | `gpt-4o-mini` | LLM for answering + reranking |
| `LLM_TEMPERATURE` | ❌ | `0.0` | LLM temperature (keep at 0 for legal precision) |
| `LLM_MAX_TOKENS` | ❌ | `1000` | Max tokens for LLM response |
| `EMBEDDING_BATCH_SIZE` | ❌ | `100` | Texts per OpenAI embedding batch |
| `TOP_K_RETRIEVAL` | ❌ | `10` | Chunks retrieved before reranking |
| `TOP_K_RERANK` | ❌ | `5` | Chunks passed to LLM after reranking |
| `CONTEXT_MAX_TOKENS` | ❌ | `4000` | Token budget for context window |
| `CACHE_TTL_SECONDS` | ❌ | `3600` | Redis query cache TTL |
| `LEGAL_ACTS_DIR` | ❌ | `/app/legal-acts` | Path to legal-acts data directory |
| `LOG_LEVEL` | ❌ | `INFO` | structlog level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `ENVIRONMENT` | ❌ | `development` | `development` (human logs) or `production` (JSON logs) |

> **Never commit `.env`** — it contains your API key. The `.gitignore` already excludes it.

---

## 7. Code Conventions

### Async Everywhere

LexGrid uses `asyncio` throughout. All database operations, HTTP calls, and Redis operations are `async/await`. Never use synchronous blocking calls inside `async def` functions.

```python
# ✅ Correct
async def get_section(act_code: str, section_number: str, session: AsyncSession) -> LegalChunk | None:
    stmt = select(SectionEmbedding).where(
        SectionEmbedding.act_code == act_code,
        SectionEmbedding.section_number == section_number,
    ).limit(1)
    result = await session.execute(stmt)
    row = result.scalars().first()
    return _orm_to_chunk(row) if row else None

# ❌ Wrong — blocks the event loop
def get_section(act_code: str, section_number: str, session: Session) -> LegalChunk | None:
    return session.query(SectionEmbedding).filter(...).first()
```

**Exception**: Celery tasks run in a synchronous context. The `embed_and_index_chunk` task uses `asyncio.run(_run())` to bridge sync Celery into async SQLAlchemy. This is intentional and correct.

### Pydantic Models for All Interfaces

Every external data boundary (API request/response, config, data models) uses Pydantic v2. This ensures type safety and automatic validation.

```python
# ✅ Correct — Pydantic enforces types and constraints
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    act_filter: Optional[str] = Field(None)   # single act code, not a list
    top_k: int = Field(default=5, ge=1, le=20)
    use_cache: bool = True
```

### Frozen Models for Immutable Data

`LegalChunk` and `Citation` use `model_config = {"frozen": True}` — they cannot be mutated after creation. `LegalChunkWithEmbedding` overrides this with `{"frozen": False}` to allow attaching the embedding vector.

```python
class LegalChunk(BaseModel):
    model_config = {"frozen": True}
    id: str
    act_code: str
    act_year: str   # NOTE: str, not int — matches JSON source format
    # ...

class LegalChunkWithEmbedding(LegalChunk):
    model_config = {"frozen": False}  # mutable to attach embedding
    embedding: Optional[list[float]] = None
```

### Structured Logging

Use `structlog` for all logging. Pass context as keyword arguments, not formatted strings:

```python
import structlog
logger = structlog.get_logger(__name__)

# ✅ Correct — structured, queryable
logger.info("query_complete", latency_ms=latency, chunks=len(chunks))
logger.warning("rerank_failed", error=str(exc))

# ❌ Wrong — unstructured string
logger.info(f"Query took {latency}ms, retrieved {len(chunks)} chunks")
```

### Type Annotations

All functions must have full type annotations. mypy is configured in `pyproject.toml`:

```python
# ✅ Correct
async def embed_texts(texts: list[str], settings: Settings) -> list[list[float]]:
    ...

# ❌ Wrong
async def embed_texts(texts, settings):
    ...
```

### Line Length

`ruff` enforces `line-length = 100`. Configure your editor to show a ruler at column 100.

### Import Style

Use `from __future__ import annotations` at the top of every module — this enables PEP 563 postponed evaluation of annotations, required for forward references and `X | Y` union syntax on Python 3.11.

---

## 8. Project Structure

```
LexGrid/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory, lifespan, router registration
│   │   ├── config.py                  # pydantic-settings, all env vars, get_settings()
│   │   ├── api/
│   │   │   ├── middleware.py          # CORS + LatencyLoggingMiddleware
│   │   │   └── routes/
│   │   │       ├── query.py           # POST /query/ — full RAG pipeline
│   │   │       ├── search.py          # GET /search/ — direct section lookup
│   │   │       ├── health.py          # GET /health — DB + Redis + OpenAI check
│   │   │       └── metrics.py         # GET /metrics/ — Prometheus plaintext
│   │   ├── retrieval/
│   │   │   ├── hybrid.py              # RRF fusion: vector + FTS → top_k chunks
│   │   │   ├── query_intelligence.py  # parse_query() — regex direct-lookup detection
│   │   │   ├── vector_retriever.py    # vector_search() → similarity_search()
│   │   │   ├── keyword_retriever.py   # keyword_search() → fts_search()
│   │   │   └── reranker.py            # rerank_chunks() — LLM-based reordering
│   │   ├── llm/
│   │   │   ├── client.py              # generate_answer() + _parse_citations()
│   │   │   ├── prompt_builder.py      # SYSTEM_PROMPT, build_context(), build_user_prompt()
│   │   │   └── context_builder.py     # build_context_window() — tiktoken token budget
│   │   ├── embeddings/
│   │   │   ├── client.py              # embed_texts() — batched, retried
│   │   │   ├── batch_processor.py     # Batch processing utilities
│   │   │   └── streaming.py           # Streaming embedding support
│   │   ├── vector_store/
│   │   │   ├── store.py               # upsert_chunk(), similarity_search(), fts_search(), get_section()
│   │   │   ├── schema.py              # SectionEmbedding ORM model
│   │   │   └── database.py            # get_engine(), get_session_factory(), async_get_session()
│   │   ├── cache/
│   │   │   ├── client.py              # get_redis_client(), ping_redis()
│   │   │   └── query_cache.py         # cache_key(), get_cached_query(), set_cached_query()
│   │   ├── models/
│   │   │   ├── chunk.py               # LegalChunk, LegalChunkWithEmbedding, ChunkType
│   │   │   ├── query.py               # QueryRequest, QueryResponse, Citation, RetrievedChunk
│   │   │   ├── search.py              # SearchRequest, SearchResponse, SectionResult
│   │   │   ├── evaluation.py          # EvalCase, EvalCaseResult, EvalReport
│   │   │   └── metrics.py             # QueryMetrics, SystemMetrics, MetricsResponse
│   │   ├── ingestion/
│   │   │   ├── loader.py              # list_available_acts(), load_act_sections()
│   │   │   ├── chunker.py             # chunk_section() → [LegalChunk, ...]
│   │   │   └── pipeline.py            # run_ingestion_pipeline() — sync orchestrator
│   │   ├── workers/
│   │   │   ├── celery_app.py          # Celery app instance + config
│   │   │   ├── batch_index_task.py    # batch_index_act() — loads + chunks + dispatches group
│   │   │   ├── embed_task.py          # embed_and_index_chunk() — embeds + upserts one chunk
│   │   │   └── reindex_task.py        # Reindex utilities
│   │   └── evaluation/
│   │       ├── test_cases.py          # EVAL_CASES — 12 ground-truth test cases
│   │       ├── metrics.py             # precision_at_k(), recall_at_k(), mrr(), legal_accuracy_score()
│   │       ├── runner.py              # run_evaluation() — async HTTP runner
│   │       └── reporter.py            # save_report(), log_failures()
│   ├── tests/
│   │   ├── test_evaluation.py
│   │   ├── test_ingestion.py
│   │   └── test_retrieval.py
│   ├── alembic/                       # Database migrations
│   ├── alembic.ini
│   ├── pyproject.toml                 # Dependencies, ruff, mypy, pytest config
│   └── Dockerfile                     # python:3.12-slim
├── ui/
│   ├── src/
│   └── package.json
├── infra/
│   ├── docker-compose.yml             # 5 services: postgres, redis, backend, celery-worker, ui
│   └── postgres/
│       └── init.sql                   # Table creation + indexes (auto-applied on first start)
├── scripts/
│   ├── ingest.py                      # CLI: dispatch batch_index_act Celery tasks
│   └── evaluate.py                    # CLI: run evaluation suite (uses click)
├── legal-acts/                        # JSON source files — one directory per act
│   ├── bns/json/sections/*.json
│   ├── cpc/json/sections/*.json
│   ├── crpc/json/sections/*.json
│   ├── hma/json/sections/*.json
│   ├── ida/json/sections/*.json
│   ├── iea/json/sections/*.json
│   ├── ipc/json/sections/*.json
│   ├── mva/json/sections/*.json
│   └── nia/json/sections/*.json
└── docs/
    ├── architecture.md
    ├── developer-guide.md             ← you are here
    ├── api-reference.md
    ├── evaluation.md
    └── ingestion.md
```

---

## 9. Running Tests

```bash
cd backend
source .venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_ingestion.py

# Run a specific test by name
pytest -k "test_chunk_section"

# Run with coverage report
pytest --cov=app --cov-report=term-missing
```

All tests use `asyncio_mode = "auto"` (configured in `pyproject.toml`) — async test functions work without `@pytest.mark.asyncio`:

```python
# ✅ This works automatically — no decorator needed
async def test_embed_query():
    result = await embed_texts(["bail conditions"], get_settings())
    assert len(result) == 1
    assert len(result[0]) == 1536
```

### Test Environment

Tests use the same `.env` file as the application. For CI, set environment variables directly. Use a separate test database to avoid polluting production data:

```bash
# For CI
DATABASE_URL=postgresql+asyncpg://lexgrid:lexgrid@localhost:5432/lexgrid_test pytest
```

---

## 10. Linting & Type Checking

```bash
cd backend

# Run ruff linter
ruff check app/

# Run ruff with auto-fix
ruff check --fix app/

# Run ruff formatter (check only)
ruff format --check app/

# Run ruff formatter (apply)
ruff format app/

# Run mypy type checker
mypy app/

# Run everything (as CI does)
ruff check app/ && ruff format --check app/ && mypy app/
```

### ruff Configuration (from `pyproject.toml`)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
# E: pycodestyle errors
# F: pyflakes (undefined names, unused imports)
# I: isort (import ordering)
# UP: pyupgrade (modern Python syntax — e.g. Optional[X] → X | None)
```

### mypy Configuration

```toml
[tool.mypy]
python_version = "3.11"
strict = false
ignore_missing_imports = true
```

`strict = false` is intentional — external libraries (SQLAlchemy async, pgvector) have incomplete type stubs and would generate excessive false positives in strict mode.

---

## 11. How to Add a New Act

Adding a new act requires changes in 3 places.

### Step 1: Prepare the Section JSON Files

Create the directory structure:
```
legal-acts/{act_code}/json/sections/
```

Each section is a separate JSON file named `section-{number}.json`:

```json
{
  "section_number": "1",
  "section_title": "Short title and commencement",
  "file_id": "section-1",
  "chapter_number": "I",
  "chapter_title": "Preliminary",
  "act_code": "xyz",
  "act_name": "Example Act",
  "act_year": "2024",
  "text": "This Act may be called the Example Act, 2024...",
  "explanations": [
    "Explanation 1.— For the purposes of this section..."
  ],
  "amendments": [],
  "source_url": "https://example.com/act/section/1"
}
```

**Field requirements** (from `ingestion/chunker.py`):
- `act_code`: lowercase, short (e.g. `xyz`) — used in chunk IDs
- `act_name`: Full legal name of the Act
- `act_year`: **string** (e.g. `"2024"`, not `2024`)
- `section_number`: string (may contain letters, e.g. `"120A"`, `"498A"`)
- `text`: Full text of the section (required, non-empty — sections with empty `text` are skipped)
- `explanations`: Optional list of explanation strings — each becomes a separate `EXPLANATION` chunk
- `source_url`: Optional but strongly recommended for citations

### Step 2: Register the Act in Query Intelligence

Edit `backend/app/retrieval/query_intelligence.py` and add the new act to `_ACT_CODE_MAP`:

```python
_ACT_CODE_MAP: dict[str, str] = {
    "IPC": "ipc",
    # ... existing entries ...
    "XYZ": "xyz",   # add this
}
```

The regex patterns are built dynamically from `_ACT_CODE_MAP.keys()`, so no regex changes are needed.

### Step 3: Run Ingestion

```bash
# From repo root, with Celery worker running
python scripts/ingest.py --act xyz

# Or re-ingest everything (safe — upsert is idempotent)
python scripts/ingest.py --act all
```

### Step 4: Verify

```bash
# Check section count for new act
psql -U lexgrid -d lexgrid -c "SELECT COUNT(*) FROM sections WHERE act_code = 'xyz';"

# Run a test query
curl -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "short title of xyz act", "act_filter": "xyz"}'
```

---

## 12. How to Add a New API Endpoint

### Step 1: Create the Route Handler

Add a new file in `backend/app/api/routes/`:

```python
# backend/app/api/routes/acts.py
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.vector_store.database import async_get_session
from app.vector_store.schema import SectionEmbedding

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/acts", tags=["acts"])


@router.get("/")
async def list_acts(
    session: AsyncSession = Depends(async_get_session),
) -> dict:
    """Return all indexed act codes with section counts."""
    result = await session.execute(
        select(SectionEmbedding.act_code, func.count().label("count"))
        .group_by(SectionEmbedding.act_code)
        .order_by(SectionEmbedding.act_code)
    )
    return {"acts": [{"act_code": row.act_code, "count": row.count} for row in result]}
```

### Step 2: Register the Router in `main.py`

```python
# backend/app/main.py
from app.api.routes import health, metrics, query, search, acts  # add acts

def create_app() -> FastAPI:
    app = FastAPI(...)
    register_middleware(app)
    app.include_router(query.router)
    app.include_router(search.router)
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(acts.router)   # add this
    return app
```

### Step 3: Add Pydantic Models (if needed)

Add request/response models to `backend/app/models/`:

```python
# backend/app/models/acts.py
from pydantic import BaseModel, Field

class ActSummary(BaseModel):
    act_code: str
    act_name: str
    section_count: int

class ActsResponse(BaseModel):
    acts: list[ActSummary]
    total: int
```

### Step 4: Write Tests

```python
# backend/tests/test_acts.py
from httpx import AsyncClient

async def test_list_acts(client: AsyncClient):
    response = await client.get("/acts/")
    assert response.status_code == 200
    data = response.json()
    assert "acts" in data
    act_codes = [a["act_code"] for a in data["acts"]]
    assert "ipc" in act_codes
```

---

## 13. Debugging Tips

### Inspect Query Logs

The `query_logs` table records every query (when instrumented):

```sql
-- Slow queries (latency > 2 seconds)
SELECT query_text, latency_ms, cache_hit
FROM query_logs
WHERE latency_ms > 2000
ORDER BY created_at DESC;

-- Cache miss rate
SELECT
    COUNT(*) FILTER (WHERE cache_hit = true)  AS hits,
    COUNT(*) FILTER (WHERE cache_hit = false) AS misses,
    ROUND(100.0 * COUNT(*) FILTER (WHERE cache_hit = true) / NULLIF(COUNT(*), 0), 1) AS hit_rate_pct
FROM query_logs;

-- Most-retrieved sections
SELECT unnest(retrieved_section_ids) AS section_id, COUNT(*) AS times_retrieved
FROM query_logs
GROUP BY section_id
ORDER BY times_retrieved DESC
LIMIT 20;
```

### Enable Debug Logging

```bash
# In backend/.env
LOG_LEVEL=DEBUG
```

With `DEBUG` level, structlog emits:
- Every cache key computed
- Every embedding call (model, input length)
- Vector retrieval scores
- FTS results
- RRF fusion results
- Reranker input/output

### Test Retrieval Without LLM

Use the `/search/` endpoint for direct section lookup (no LLM, no embedding):

```bash
# Direct lookup: act_code + section_number
curl "http://localhost:8000/search/?act_code=ipc&section_number=300"
```

This is useful for verifying that a section is indexed correctly.

### Source Page Integration Checklist (Markdown + Citation Links)

Use this quick checklist after any UI/API changes related to sources/citations:

```bash
# 1) Original citation route should load and render markdown source
curl -i "http://localhost:3000/section/crpc/149"

# 2) Alphanumeric section route should load (canonical format)
curl -i "http://localhost:3000/section/ipc/120A"

# 3) Variant route format should still resolve (normalization)
curl -i "http://localhost:3000/section/IPC/120-a"

# 4) Source API should return markdown payload for existing section
curl "http://localhost:8000/source/?act_code=crpc&section_number=149"

# 5) Source API should normalize variant section strings
curl "http://localhost:8000/source/?act_code=IPC&section_number=Section%20120-a"
```

Expected outcomes:
- `/section/...` pages return `200 OK` for known sections.
- Source page shows **Canonical Source (Markdown)** with a valid `source_markdown_path`.
- Breadcrumb labels are normalized (e.g., `IPC › Section 120A`).
- `/source/` returns `source_markdown_found: true` for existing sections.
- Missing sections return not found behavior on the page and `source_markdown_found: false` from `/source/`.

### Inspect Embeddings

```sql
-- Check a section has an embedding
SELECT id, act_code, section_number, token_count,
       embedding IS NOT NULL AS has_embedding,
       length(content) AS content_length
FROM sections
WHERE act_code = 'ipc' AND section_number = '300';

-- Count sections without embeddings (ingestion incomplete)
SELECT act_code,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE embedding IS NULL) AS missing_embeddings
FROM sections
GROUP BY act_code
ORDER BY act_code;
```

### Redis Cache Inspection

```bash
# Connect to Redis (db=0 is the query cache)
redis-cli

# List all cached query keys
KEYS query:*

# Check TTL of a cached key
TTL query:abc123...

# Get a cached value (JSON)
GET query:abc123...

# See total key count in db=0
DBSIZE

# Flush the query cache (db=0) without touching Celery (db=1, db=2)
SELECT 0
FLUSHDB
```

### Celery Worker Debugging

```bash
# Run worker in foreground with debug logging
celery -A app.workers.celery_app worker --loglevel=debug --concurrency=1

# Inspect active tasks
celery -A app.workers.celery_app inspect active

# Inspect registered tasks
celery -A app.workers.celery_app inspect registered

# Monitor with Flower (web UI)
pip install flower
celery -A app.workers.celery_app flower
# Open http://localhost:5555
```

### Verify Ingestion Completed

```bash
# Check section counts per act
psql -U lexgrid -d lexgrid -c "
SELECT act_code, COUNT(*) AS sections, COUNT(embedding) AS with_embeddings
FROM sections
GROUP BY act_code
ORDER BY act_code;
"
```

All sections should have embeddings. If `with_embeddings < sections`, some `embed_and_index_chunk` tasks failed — check Celery logs.

---

## 14. Common Pitfalls

### Trailing Slash on `/query/`

**Problem**: `POST /query` (no trailing slash) returns a 307 redirect. `httpx` does NOT follow redirects on POST requests by default — you'll get an empty response or a redirect error.

**Fix**: Always use `POST /query/` (with trailing slash):

```python
# ✅ Correct
response = await client.post("http://localhost:8000/query/", json=payload)

# ❌ Wrong — 307 redirect, httpx won't follow it for POST
response = await client.post("http://localhost:8000/query", json=payload)
```

This is FastAPI's default behaviour (redirect non-slash → slash). The evaluation runner explicitly uses the trailing slash.

### `act_filter` is a String, Not a List

**Problem**: Sending `"act_filter": ["ipc", "crpc"]` (a list) in the request body.

**Fix**: `act_filter` is `Optional[str]` — a single act code:

```python
# ✅ Correct
{"query": "murder", "act_filter": "ipc"}

# ❌ Wrong — will fail validation
{"query": "murder", "act_filter": ["ipc", "crpc"]}
```

To search across multiple acts, omit `act_filter` entirely (searches all acts).

### PYTHONPATH Not Set

**Problem**: `ModuleNotFoundError: No module named 'app'` when running scripts outside Docker.

**Fix**: The scripts handle this automatically by inserting `backend/` into `sys.path`. Run from the repo root:

```bash
# ✅ Correct — run from repo root
python scripts/ingest.py --act ipc
python scripts/evaluate.py

# ❌ Wrong — wrong working directory
cd scripts && python ingest.py
```

In Docker, `ENV PYTHONPATH=/app` is set in the Dockerfile.

### Asyncpg URL Format

**Problem**: Using `postgresql://` (psycopg2 sync) instead of `postgresql+asyncpg://`.

**Fix**: Always use `postgresql+asyncpg://` in `DATABASE_URL`:

```bash
# ✅ Correct
DATABASE_URL=postgresql+asyncpg://lexgrid:lexgrid@localhost:5432/lexgrid

# ❌ Wrong — will fail at runtime with SQLAlchemy async
DATABASE_URL=postgresql://lexgrid:lexgrid@localhost:5432/lexgrid
```

### `act_year` is a String

**Problem**: Passing `act_year` as an integer in section JSON files.

**Fix**: `LegalChunk.act_year` is `str`. The JSON source files must use string values:

```json
// ✅ Correct
{"act_year": "1860"}

// ❌ Wrong — Pydantic will coerce it, but be explicit
{"act_year": 1860}
```

### Embedding Model Mismatch After Re-ingestion

**Problem**: Changing `EMBEDDING_MODEL` after ingestion produces incorrect similarity results — new query embeddings are from a different vector space than stored document embeddings.

**Fix**: If you change `EMBEDDING_MODEL`, re-ingest all acts:
```bash
python scripts/ingest.py --act all
```

Ingestion is idempotent (upsert) — safe to re-run.

### IVFFlat Index Needs ANALYZE After Bulk Ingest

**Problem**: After a large bulk ingestion, the IVFFlat index may return suboptimal results until PostgreSQL updates its statistics.

**Fix**: Run ANALYZE after bulk ingestion:
```bash
psql -U lexgrid -d lexgrid -c "ANALYZE sections;"
```
