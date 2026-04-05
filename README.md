# ⚖️ LexGrid 📜

A production-grade Retrieval-Augmented Generation (RAG) system for 🇮🇳 Indian Bare Acts ⚖️. Query 9 major Indian laws in plain English and get precise, cited answers grounded strictly in statutory text.

> **100% evaluation pass rate** across 12 test cases including negative (out-of-domain) tests. Built to never hallucinate — if the answer isn't in the law, LexGrid says so.

---

## Table of Contents

- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Environment Variables](#environment-variables)
- [Available Scripts](#available-scripts)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Evaluation](#evaluation)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Key Features

- **Hybrid Retrieval** — Combines pgvector ANN search with PostgreSQL full-text search (tsvector), fused via Reciprocal Rank Fusion (RRF k=60) for superior recall and precision
- **Query Intelligence** — Regex-based detection of "Section 302 IPC"-style queries bypasses embedding entirely and hits the database directly, returning sub-10ms responses
- **Anti-Hallucination** — LLM temperature=0, strict 5-rule system prompt, answers grounded only to retrieved context, mandatory `[Section X, Act Name]` citations
- **Out-of-Domain Rejection** — Cosine distance threshold (0.75) means physics questions and other off-topic queries return empty results and a clean "cannot find" response — no fabrication
- **Redis Query Cache** — SHA256-keyed cache (TTL 3600s) for repeated queries, with cache-hit flag in every API response
- **Async Ingestion** — Celery workers with Redis broker handle embedding + upsert in the background, enabling non-blocking ingestion of entire acts
- **Evaluation Suite** — 12 test cases covering direct lookup, comparative, procedural, and negative query types with P@K, Recall@K, MRR, and Legal Accuracy metrics
- **9 Indian Acts** — BNS, CPC, CrPC, HMA, IDA, IEA, IPC, MVA, NIA (~2,284 sections indexed)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **API** | FastAPI ≥0.111.0, Python 3.11+, uvicorn[standard] |
| **Embeddings** | OpenAI `text-embedding-3-small` (1536-dim) via OpenRouter |
| **LLM** | `gpt-4o-mini` via OpenRouter, temperature=0 |
| **Vector Store** | PostgreSQL 16 + pgvector extension |
| **Full-Text Search** | PostgreSQL tsvector/tsquery (GENERATED ALWAYS, GIN index) |
| **Cache** | Redis 7 (query cache TTL 3600s) |
| **Task Queue** | Celery 5 + Redis broker (concurrency=4) |
| **UI** | Next.js + Tailwind CSS |
| **ORM** | SQLAlchemy async (asyncpg driver) |
| **Config** | pydantic-settings (all env-var driven) |
| **Logging** | structlog (structured JSON logs) |
| **Token Counting** | tiktoken (cl100k_base), 4000-token context budget |
| **Linting** | ruff (line-length=100) |
| **Type Checking** | mypy |
| **Testing** | pytest, pytest-asyncio |
| **Build** | hatchling |
| **Infra** | Docker Compose (5 containers) |

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/install/) v2+ (`docker compose`, not `docker-compose`)
- An [OpenRouter](https://openrouter.ai/) API key (used for both embedding and LLM calls)
- `curl` or any HTTP client (for testing the API)

No Python, Node.js, or PostgreSQL installation is needed locally — everything runs in Docker.

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/srajasimman/lexgrid.git
cd lexgrid
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
```

Open `.env` and configure at minimum:

```env
# Required: your OpenRouter API key
OPENAI_API_KEY=sk-or-v1-your-openrouter-key-here
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# These defaults work with Docker Compose as-is
DATABASE_URL=postgresql+asyncpg://lexgrid:lexgrid@lexgrid-postgres:5432/lexgrid
REDIS_URL=redis://lexgrid-redis:6379/0
CELERY_BROKER_URL=redis://lexgrid-redis:6379/1
CELERY_RESULT_BACKEND=redis://lexgrid-redis:6379/2
```

See [Environment Variables](#environment-variables) for the full reference.

### 3. Start All Services

```bash
docker compose -f infra/docker-compose.yml up -d
```

This starts 5 containers:

| Container | Role | Port |
|-----------|------|------|
| `lexgrid-postgres` | PostgreSQL 16 + pgvector | 5432 |
| `lexgrid-redis` | Redis 7 (cache + broker) | 6379 |
| `lexgrid-backend` | FastAPI API | 8000 |
| `lexgrid-celery` | Celery worker (concurrency=4) | — |
| `lexgrid-ui` | Next.js frontend | 3000 |

Wait ~15 seconds for PostgreSQL to initialize, then verify everything is healthy:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy","database":"connected","redis":"connected","version":"0.1.0"}
```

### 4. Ingest Legal Data

Ingest all 9 acts (dispatches async Celery tasks for embedding and upsert):

```bash
docker exec lexgrid-backend python scripts/ingest.py --act all
```

Or ingest specific acts:

```bash
docker exec lexgrid-backend python scripts/ingest.py --act ipc,crpc,bns
```

Monitor ingestion progress:

```bash
docker compose -f infra/docker-compose.yml logs celery -f
```

Ingestion of all 9 acts takes **~5–10 minutes** depending on OpenRouter API latency. When done, verify:

```bash
docker exec lexgrid-postgres psql -U lexgrid -d lexgrid \
  -c "SELECT act_code, COUNT(*) FROM sections GROUP BY act_code ORDER BY act_code;"
```

### 5. Query the API

```bash
curl -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the punishment for murder under IPC?",
    "top_k": 5
  }'
```

> **Important**: The `/query/` endpoint requires a trailing slash. See [Troubleshooting](#post-query-returns-307-redirect).

Expected response:

```json
{
  "answer": "Under Section 302 of the Indian Penal Code, whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine. [Section 302, Indian Penal Code]",
  "citations": [
    {
      "act_code": "ipc",
      "act_name": "Indian Penal Code",
      "section_number": "302",
      "section_title": "Punishment of murder",
      "source_url": "https://..."
    }
  ],
  "retrieved_chunks": [...],
  "query": "What is the punishment for murder under IPC?",
  "cache_hit": false,
  "latency_ms": 1243.7
}
```

### 6. Open the UI

Navigate to [http://localhost:3000](http://localhost:3000) for the Next.js query interface.

API auto-docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                         │
│                                                                 │
│  POST /query/                                                   │
│       │                                                         │
│       ├─► Redis Cache (SHA256 key, TTL 3600s)                   │
│       │      └── HIT → return cached response                   │
│       │                                                         │
│       └─► Query Intelligence (regex)                            │
│              ├── "Section 302 IPC" → Direct DB Lookup           │
│              └── Natural language → Hybrid Retrieval            │
│                        │                                        │
│              ┌─────────┴──────────┐                             │
│              │                    │                             │
│         pgvector ANN         PostgreSQL FTS                     │
│         (cosine dist)        (tsvector GIN)                     │
│              │                    │                             │
│              └─────────┬──────────┘                             │
│                        │                                        │
│                   RRF Fusion (k=60)                             │
│                        │                                        │
│                  LLM Reranker                                   │
│                  (gpt-4o-mini)                                  │
│                        │                                        │
│              Context Builder (4000 tokens)                      │
│                        │                                        │
│                  LLM Answer                                     │
│                  (gpt-4o-mini, temp=0)                          │
│                        │                                        │
│              Citation Parser + Cache Write                      │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
lexgrid/
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│       ├── main.py                  # FastAPI app factory, lifespan, CORS
│       ├── config.py                # pydantic-settings (all env vars)
│       ├── api/routes/
│       │   ├── query.py             # POST /query/ — main RAG endpoint
│       │   ├── search.py            # GET /search/ — raw retrieval, no LLM
│       │   └── health.py            # GET /health, GET /metrics
│       ├── retrieval/
│       │   ├── hybrid.py            # RRF fusion of vector + keyword results
│       │   ├── query_intelligence.py # Regex direct section lookup
│       │   ├── vector_retriever.py  # pgvector cosine ANN search
│       │   ├── keyword_retriever.py # PostgreSQL tsvector FTS
│       │   └── reranker.py          # LLM reranking (gpt-4o-mini, temp=0)
│       ├── llm/
│       │   ├── client.py            # OpenAI async client (OpenRouter)
│       │   ├── prompt_builder.py    # System prompt + user prompt assembly
│       │   └── context_builder.py   # tiktoken context window (4000 tokens)
│       ├── vector_store/
│       │   ├── store.py             # Upsert, ANN search, direct lookup
│       │   ├── schema.py            # SQLAlchemy Section ORM model
│       │   └── database.py          # Async engine factory (lru_cache)
│       ├── cache/
│       │   ├── client.py            # Redis async client
│       │   └── query_cache.py       # SHA256-keyed cache (get/set/invalidate)
│       ├── models/
│       │   ├── chunk.py             # LegalChunk, LegalChunkWithEmbedding
│       │   └── query.py             # QueryRequest, QueryResponse, Citation
│       ├── ingestion/
│       │   ├── chunker.py           # JSON → LegalChunk (section + explanation)
│       │   └── pipeline.py          # Embed + upsert pipeline (Celery task body)
│       ├── workers/
│       │   └── celery_app.py        # Celery app config, autodiscover tasks
│       └── evaluation/
│           ├── test_cases.py        # 12 test cases
│           └── metrics.py           # P@K, Recall@K, MRR, Legal Accuracy
├── infra/
│   ├── docker-compose.yml           # 5-container stack
│   └── postgres/init.sql            # Schema: sections table, pgvector, GIN index
├── scripts/
│   ├── ingest.py                    # CLI: dispatch Celery ingestion tasks
│   └── evaluate.py                  # CLI: run evaluation suite → JSON report
├── legal-acts/                      # Raw JSON source data (per act)
├── frontend/                        # Next.js + Tailwind UI
└── docs/
    ├── architecture.md              # System design deep-dive
    ├── developer-guide.md           # Local dev, conventions, adding acts
    ├── api-reference.md             # Full API spec with examples
    ├── evaluation.md                # Evaluation framework and test cases
    └── ingestion.md                 # Data pipeline: JSON → pgvector
```

### RAG Pipeline (Step by Step)

For a query like `"What is the punishment for murder under IPC?"`:

1. **Cache Check** — SHA256 key = `query:{sha256(query.lower() + sorted(act_codes))}`. Cache hit → return immediately with `cache_hit: true`.

2. **Query Intelligence** — Two regex patterns checked:
   - `_PATTERN_SECTION_FIRST` — matches "Section 302 IPC", "Section 120A CrPC"
   - `_PATTERN_ACT_FIRST` — matches "IPC 302", "BNS Section 103"
   - Match → direct DB lookup by `(act_code, section_number)`. **No embedding, no vector search.**

3. **Embedding** — Query text → `text-embedding-3-small` → 1536-dim float vector (OpenRouter)

4. **Vector Search** — IVFFlat index (`lists=100`, `vector_cosine_ops`) returns top-K with distance ≤ 0.75. Out-of-domain queries return 0 results here and short-circuit immediately.

5. **Keyword Search** — tsvector FTS with weighted fields:
   - Weight A: `section_title` (highest relevance)
   - Weight B: `act_name`
   - Weight C: `content`

6. **RRF Fusion** — `score(d) = Σ 1 / (60 + rank(d))`. Documents in both result sets score significantly higher.

7. **Short-Circuit** — If both retrievers return empty → return `[]`, skip reranker + LLM entirely.

8. **Reranker** — Top fused results sent to `gpt-4o-mini` for LLM-based relevance reranking. Falls back to RRF order on any LLM failure.

9. **Context Building** — tiktoken (cl100k_base) counts tokens. Chunks added greedily top-to-bottom until 4000-token budget exhausted.

10. **LLM Answer** — System prompt + context + query → `gpt-4o-mini` (temperature=0). Always cites in format `[Section X, Act Name]`.

11. **Citation Parsing** — Regex extracts citations from LLM answer → typed `Citation` objects.

12. **Cache Write** — Response written to Redis with TTL 3600s.

13. **Query Logging** — Every query logged to `query_logs` PostgreSQL table (text, hash, retrieved_section_ids, latency_ms, cache_hit).

### Why Hybrid Retrieval?

Pure vector search misses exact legal references. Searching "Section 302" semantically finds related concepts but may not rank the exact section first. Pure keyword search misses natural language questions like "what constitutes culpable homicide?". RRF fusion gives you both — documents relevant to either signal get a score boost, and documents relevant to both score highest.

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenRouter (or OpenAI) API key | `sk-or-v1-...` |
| `OPENAI_BASE_URL` | API base URL | `https://openrouter.ai/api/v1` |
| `DATABASE_URL` | Async PostgreSQL DSN | `postgresql+asyncpg://lexgrid:lexgrid@lexgrid-postgres:5432/lexgrid` |
| `REDIS_URL` | Redis for query cache (db=0) | `redis://lexgrid-redis:6379/0` |
| `CELERY_BROKER_URL` | Redis for Celery broker (db=1) | `redis://lexgrid-redis:6379/1` |
| `CELERY_RESULT_BACKEND` | Redis for Celery results (db=2) | `redis://lexgrid-redis:6379/2` |

### Optional (with defaults)

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_MODEL` | LLM model identifier | `gpt-4o-mini` |
| `EMBEDDING_MODEL` | Embedding model identifier | `text-embedding-3-small` |
| `LLM_TEMPERATURE` | LLM temperature (0 = deterministic) | `0` |
| `CACHE_TTL` | Redis query cache TTL in seconds | `3600` |
| `TOP_K` | Default number of retrieved chunks | `5` |
| `MAX_DISTANCE` | Cosine distance cutoff for vector search | `0.75` |

### Why OpenRouter Instead of OpenAI Directly?

OpenRouter provides an OpenAI-compatible API that routes to multiple model providers. The same OpenAI Python SDK works with `base_url=OPENAI_BASE_URL`. This means you can switch from `gpt-4o-mini` to `claude-3-haiku` or `mistral-7b` by changing one environment variable — no code changes.

---

## Available Scripts

| Script | Command | Description |
|--------|---------|-------------|
| **Ingest all acts** | `python scripts/ingest.py --act all` | Dispatch Celery tasks for all 9 acts |
| **Ingest specific acts** | `python scripts/ingest.py --act ipc,crpc` | Acts: bns, cpc, crpc, hma, ida, iea, ipc, mva, nia |
| **Run evaluation** | `python scripts/evaluate.py --api-url http://localhost:8000 --output eval_report.json` | Run 12-case eval suite |
| **Lint** | `ruff check .` | Check Python style (line-length=100, rules E/F/I/UP) |
| **Auto-fix lint** | `ruff check . --fix` | Fix auto-fixable lint issues |
| **Type check** | `mypy backend/` | Run mypy type checks |
| **Tests** | `pytest backend/tests/ -v` | Run test suite |

---

## API Reference

### POST /query/

The main RAG endpoint. Returns a cited, LLM-generated answer.

> **Trailing slash required.** FastAPI redirects `/query` → `/query/` with HTTP 307. httpx does not follow 307 redirects on POST requests.

**Request:**
```json
{
  "query": "What is the punishment for murder?",
  "act_filter": ["ipc"],
  "top_k": 5,
  "use_cache": true
}
```

**Response:**
```json
{
  "answer": "Section 302 IPC: Whoever commits murder shall be punished with death...",
  "citations": [{"act_code": "ipc", "section_number": "302", ...}],
  "retrieved_chunks": [...],
  "cache_hit": false,
  "latency_ms": 1200.3
}
```

**Errors:**
- `422` — Validation error (query too short/long, top_k out of range)
- `503` — LLM or database unavailable

### GET /search/

Raw retrieval without LLM synthesis. Use for debugging retrieval quality.

```bash
curl "http://localhost:8000/search/?q=murder+punishment&act=ipc&top_k=3"
```

### GET /health

```bash
curl http://localhost:8000/health
# {"status":"healthy","database":"connected","redis":"connected","version":"0.1.0"}
```

### GET /metrics

Query log statistics and section counts.

See [`docs/api-reference.md`](docs/api-reference.md) for full specification with all fields and curl examples.

---

## Testing

```bash
# Run all tests
docker exec lexgrid-backend pytest backend/tests/ -v

# Run with coverage
docker exec lexgrid-backend pytest backend/tests/ --cov=app --cov-report=term-missing
```

Test configuration in `pyproject.toml`:
- `asyncio_mode = "auto"` — async test functions work without `@pytest.mark.asyncio`
- Tests use actual async DB/Redis connections (integration tests)

---

## Evaluation

```bash
docker exec lexgrid-backend \
  python scripts/evaluate.py \
    --api-url http://localhost:8000 \
    --output eval_report.json
```

### Latest Benchmark Results

| Metric | Score |
|--------|-------|
| Pass Rate | 100% (12/12) |
| MRR | 0.833 |
| Recall@5 | 0.814 |
| P@5 | 0.233 |
| Legal Accuracy | 0.703 |

### Test Case Types

| Type | Count | Purpose |
|------|-------|---------|
| Direct lookup | 4 | Verify exact section retrieval |
| Comparative | 3 | Multi-section reasoning |
| Procedural | 3 | Multi-step legal process queries |
| Negative (out-of-domain) | 2 | Verify hallucination rejection |

Negative tests (tc-06: dowry under HMA, tc-12: quantum physics) confirm LexGrid correctly refuses to answer when relevant law is absent from the index.

See [`docs/evaluation.md`](docs/evaluation.md) for all 12 test case definitions and how to add new ones.

---

## Deployment

Docker Compose is the primary deployment method. The entire stack is self-contained.

### Quick Deploy

```bash
# Build and start all services
docker compose -f infra/docker-compose.yml up -d --build

# Verify health
curl http://localhost:8000/health

# Ingest data (first-time setup)
docker exec lexgrid-backend python scripts/ingest.py --act all

# Validate quality
docker exec lexgrid-backend python scripts/evaluate.py \
  --api-url http://localhost:8000 --output eval_report.json
```

### Production Checklist

- [ ] Set a strong PostgreSQL password (not the default `lexgrid`)
- [ ] Use a persistent Redis instance (or enable RDB/AOF persistence)
- [ ] Set `OPENAI_API_KEY` to a valid, rate-limit-sufficient key
- [ ] Place nginx or a load balancer in front of port 8000
- [ ] Confirm section count after ingestion (`SELECT COUNT(*) FROM sections` → ~2284)
- [ ] Run `evaluate.py` and confirm 100% pass rate

### View Logs

```bash
# All services
docker compose -f infra/docker-compose.yml logs -f

# Backend API only
docker compose -f infra/docker-compose.yml logs backend -f

# Celery ingestion worker
docker compose -f infra/docker-compose.yml logs celery -f
```

### Stop / Reset

```bash
# Stop (data preserved in volumes)
docker compose -f infra/docker-compose.yml down

# Full reset (destroys all data — re-ingestion required)
docker compose -f infra/docker-compose.yml down -v
```

---

## Troubleshooting

### POST /query/ Returns 307 Redirect

**Cause**: Missing trailing slash. FastAPI redirects `/query` → `/query/` via HTTP 307. httpx does not follow 307 on POST requests.

**Fix**: Use `POST http://localhost:8000/query/` (note the `/`).

---

### Query Returns "I cannot find this information"

**Check 1 — Is data ingested?**
```bash
docker exec lexgrid-postgres psql -U lexgrid -d lexgrid \
  -c "SELECT COUNT(*) FROM sections;"
# Should be ~2284. If 0, run: docker exec lexgrid-backend python scripts/ingest.py --act all
```

**Check 2 — Is the act in scope?**
LexGrid only covers 9 acts: `bns, cpc, crpc, hma, ida, iea, ipc, mva, nia`. Questions about other laws correctly return no results.

**Check 3 — Is distance threshold too strict?**
Default `MAX_DISTANCE=0.75`. Try setting to `0.85` in `.env` and restarting the backend.

---

### IVFFlat Index Warning at Startup

**Cause**: pgvector logs a warning when building an IVFFlat index (`lists=100`) with fewer rows than `lists`. This is expected on a fresh database before ingestion.

**Fix**: Run `scripts/ingest.py`. The warning disappears once rows are loaded.

---

### Celery Tasks Not Processing

```bash
# Check worker is running
docker compose -f infra/docker-compose.yml ps celery

# Check worker logs
docker compose -f infra/docker-compose.yml logs celery --tail=50

# Test Redis broker connectivity
docker exec lexgrid-backend python -c \
  "import redis; r=redis.from_url('redis://lexgrid-redis:6379/1'); print(r.ping())"
# Should print: True
```

---

### Database Connection Refused

**Cause**: `DATABASE_URL` points to `localhost` instead of the container name.

**Fix**: Use `lexgrid-postgres` as the hostname in `DATABASE_URL`:
```
DATABASE_URL=postgresql+asyncpg://lexgrid:lexgrid@lexgrid-postgres:5432/lexgrid
```

Docker Compose places all containers on the same network. Container-to-container communication uses service names, not `localhost`.

---

## Contributing

1. Fork the repository and create a feature branch: `git checkout -b feat/your-feature`
2. Follow code conventions (see below)
3. Add/update tests for changed retrieval logic
4. Run the evaluation suite and confirm 100% pass rate
5. Open a pull request with a clear description of what changed and **why**

### Code Conventions

- **Linting**: `ruff check . --fix` (line-length=100, rules E/F/I/UP)
- **Types**: `mypy backend/` — all public functions must be typed
- **Logging**: `structlog.get_logger()` — never `print()` or raw `logging`
- **Async**: All I/O operations must be async (`asyncpg`, `aioredis`, `httpx`)
- **Config**: All settings go through `app/config.py` pydantic-settings — no hardcoded values

---

## License

MIT License — see [LICENSE](LICENSE) for details.
