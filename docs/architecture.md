# LexGrid Architecture

> **Why this document exists**: Understanding *why* the system is built this way is as important as knowing *what* it does. Every architectural decision here was made to solve a specific legal-domain problem — hallucination prevention, query precision, latency, and correctness at scale.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Container Architecture](#2-container-architecture)
3. [RAG Pipeline — End to End](#3-rag-pipeline--end-to-end)
4. [Query Intelligence](#4-query-intelligence)
5. [Hybrid Retrieval (Vector + FTS + RRF)](#5-hybrid-retrieval-vector--fts--rrf)
6. [Reranking](#6-reranking)
7. [Context Building & Token Budget](#7-context-building--token-budget)
8. [LLM Layer & Anti-Hallucination](#8-llm-layer--anti-hallucination)
9. [Caching Architecture](#9-caching-architecture)
10. [Database Schema](#10-database-schema)
11. [Ingestion Pipeline](#11-ingestion-pipeline)
12. [Observability](#12-observability)
13. [Key Numbers at a Glance](#13-key-numbers-at-a-glance)

---

## 1. System Overview

LexGrid is a **production-grade Retrieval-Augmented Generation (RAG) system** purpose-built for Indian Bare Acts. It answers natural-language legal questions by retrieving authoritative statute text and grounding the LLM response entirely within that retrieved context.

```
┌────────────────────────────────────────────────────────────────────────┐
│                            LexGrid System                              │
│                                                                        │
│   ┌──────────┐      ┌─────────────────────────────────────────────┐    │
│   │  Next.js │      │              FastAPI Backend                │    │
│   │    UI    │─────▶│                                             │    │
│   │  :3000   │      │  ┌─────────────┐    ┌────────────────────┐  │    │
│   └──────────┘      │  │ POST /query/│    │  GET /search/      │  │    │
│                     │  │ GET /health │    │  GET /metrics/     │  │    │
│                     │  └──────┬──────┘    └────────────────────┘  │    │
│                     │         │                                   │    │
│                     │  ┌──────▼───────────────────────────────┐   │    │
│                     │  │         Query Intelligence           │   │    │
│                     │  │   parse_query() → direct | semantic  │   │    │
│                     │  └──────┬────────────────────┬──────────┘   │    │
│                     │         │ semantic           │ direct       │    │
│                     │  ┌──────▼──────┐    ┌────────▼───────┐      │    │
│                     │  │   Redis     │    │   get_section  │      │    │
│                     │  │   Cache     │    │   (DB lookup)  │      │    │
│                     │  └──────┬──────┘    └────────┬───────┘      │    │
│                     │    miss │                    │              │    │
│                     │  ┌──────▼───────────────┐    │              │    │
│                     │  │  embed_texts()       │    │              │    │
│                     │  │  (text-embedding-    │    │              │    │
│                     │  │   3-small)           │    │              │    │
│                     │  └──────┬───────────────┘    │              │    │
│                     │         │                    │              │    │
│                     │  ┌──────▼───────────────┐    │              │    │
│                     │  │  hybrid_retrieve()   │    │              │    │
│                     │  │  vector + FTS + RRF  │    │              │    │
│                     │  └──────┬───────────────┘    │              │    │
│                     │         │                    │              │    │
│                     │  ┌──────▼─────────────────┐  │              │    │
│                     │  │  rerank_chunks() (LLM) │  │              │    │
│                     │  └──────┬─────────────────┘  │              │    │
│                     │         │                    │              │    │
│                     │  ┌──────▼─────────────────┐  │              │    │
│                     │  │  generate_answer()     │  │              │    │
│                     │  │  build_context() +     │◀─┘              │    │
│                     │  │  gpt-4o-mini           │                 │    │
│                     │  └──────┬─────────────────┘                 │    │
│                     │         │                                   │    │
│                     │  ┌──────▼─────────────────┐                 │    │
│                     │  │  QueryResponse +       │                 │    │
│                     │  │  Citations             │                 │    │
│                     │  └────────────────────────┘                 │    │
│                     └─────────────────────────────────────────────┘    │
│                                                                        │
│   ┌─────────────────┐        ┌───────────────────┐                     │
│   │  PostgreSQL 16  │        │     Redis 7       │                     │
│   │  + pgvector     │        │  Cache + Broker   │                     │
│   │     :5432       │        │     :6379         │                     │
│   └─────────────────┘        └───────────────────┘                     │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                     Celery Worker                              │   │
│   │   batch_index_act → group(embed_and_index_chunk × N chunks)    │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Container Architecture

Five containers defined in `infra/docker-compose.yml`:

| Container | Image | Port | Role |
|---|---|---|---|
| `lexgrid-postgres` | `pgvector/pgvector:pg16` | 5432 | Primary datastore — sections, embeddings, FTS, query logs |
| `lexgrid-redis` | `redis:7-alpine` | 6379 | Query result cache (db=0) + Celery broker (db=1) + Celery results (db=2) |
| `lexgrid-backend` | `backend/Dockerfile` | 8000 | FastAPI + uvicorn (1 worker) |
| `lexgrid-celery` | same as backend | — | Celery worker — `batch_index_act` + `embed_and_index_chunk` tasks |
| `lexgrid-ui` | `ui/Dockerfile` | 3000 | Next.js + Tailwind frontend |

**Important details**:
- The postgres image is `pgvector/pgvector:pg16` (not plain `postgres:16`) — pgvector is pre-installed.
- Redis is configured with `--maxmemory 512mb --maxmemory-policy allkeys-lru` — it will evict LRU keys when full rather than erroring.
- The backend and Celery worker use the same image. The Celery container overrides the default `CMD` with `celery -A app.workers.celery_app worker --loglevel=info --concurrency=4`.
- **Build context**: `context: ..` (repo root) so `COPY backend/` and `COPY scripts/` both work from the Dockerfile.
- **`ENV PYTHONPATH=/app`** is set in the Dockerfile — all `app.*` imports resolve correctly inside containers.
- The backend Dockerfile uses **Python 3.12-slim** (not 3.11).

---

## 3. RAG Pipeline — End to End

Every query follows this exact path. Step numbers map to source files.

```
User Query
    │
    ▼
[1] POST /query/                         ← api/routes/query.py
    │   Validate: query 3–2000 chars, top_k 1–20
    │   act_filter: optional single act code string
    │
    ▼
[2] parse_query(request.query)           ← retrieval/query_intelligence.py
    │   Two regex patterns checked:
    │   - "Section 120A IPC" → direct_lookup=True
    │   - "IPC 302" / "BNS Section 103" → direct_lookup=True
    │   - Everything else → direct_lookup=False
    │
    ├─── direct_lookup=True ─────────────────────────────────────────────┐
    │    get_section(act_code, section_number, session)                  │
    │    → single SELECT by act_code + section_number                    │
    │    Skip steps 3–8 entirely                                         │
    │    Jump to [9] generate_answer()                                   │
    │                                                                    │
    ▼ direct_lookup=False                                                │
[3] cache_key(query, act_codes)          ← cache/query_cache.py          │
    │   Key: "query:" + SHA256(query.strip().lower() + "|" +             │
    │         ",".join(sorted(act_codes or [])))                         │
    │                                                                    │
    ├─── cache HIT → return cached QueryResponse (cache_hit=True)        │
    │                                                                    │
    ▼ cache MISS                                                         │
[4] embed_texts([request.query], settings) ← embeddings/client.py        │
    │   Model: text-embedding-3-small (1536-dim)                         │
    │   Via settings.openai_base_url (OpenAI or OpenRouter)              │
    │   Retry: tenacity, 5 attempts, exponential backoff 1–60s           │
    │                                                                    │
    ▼                                                                    │
[5] hybrid_retrieve(query, embedding,    ← retrieval/hybrid.py           │
        act_codes, top_k_retrieval,                                      │
        session)                                                         │
    │                                                                    │
    │   [5a] vector_search() → similarity_search()                       │
    │        cosine distance < 0.75, top_k_retrieval * 2 candidates      │
    │                                                                    │
    │   [5b] keyword_search() → fts_search()                             │
    │        plainto_tsquery('english', query)                           │
    │        GIN index on fts_vector (GENERATED ALWAYS tsvector)         │
    │        top_k_retrieval * 2 candidates                              │
    │                                                                    │
    │   [5c] Short-circuit: if both empty → return []                    │
    │        (LLM never called for out-of-domain queries)                │
    │                                                                    │
    │   [5d] _reciprocal_rank_fusion([vector_results, keyword_results])  │
    │        RRF k=60: score = Σ 1/(60 + rank_i)                         │
    │        Returns top_k_retrieval chunks                              │
    │                                                                    │
    ▼                                                                    │
[6] rerank_chunks(query, chunks,         ← retrieval/reranker.py         │
        top_k_rerank, settings)                                          │
    │   Sends chunk summaries to gpt-4o-mini                             │
    │   Returns JSON array of reordered indices                          │
    │   Falls back to original order on any failure                      │
    │   Returns top_k_rerank chunks                                      │
    │                                                                    │
    ▼                                    ◀───────────────────────────────┘
[7] generate_answer(query, chunks,       ← llm/client.py
        settings)
    │
    │   build_context(chunks)            ← llm/prompt_builder.py
    │     Formats each chunk as:
    │     [Section {num} — {act_name} ({act_year})]
    │     {content}
    │
    │   build_system_prompt()            ← llm/prompt_builder.py
    │     5-rule anti-hallucination prompt
    │
    │   build_user_prompt(query, context)
    │     "Context:\n{context}\n\nQuestion: {query}\n\nAnswer (cite all relevant sections):"
    │
    │   AsyncOpenAI.chat.completions.create(
    │     model=settings.llm_model,      # gpt-4o-mini
    │     temperature=settings.llm_temperature,  # 0.0
    │     max_tokens=1024
    │   )
    │
    │   _parse_citations(answer, chunks)
    │     Regex: \[Section\s+([\dA-Za-z]+)\s*,\s*([^\]]+)\]
    │     Returns list[Citation]
    │
    ▼
[8] Build QueryResponse
    │   answer, citations, retrieved_chunks, query, cache_hit=False, latency_ms
    │
    ▼
[9] set_cached_query(key, response, ttl, redis)
    │   Stores QueryResponse as JSON in Redis (semantic queries only)
    │   TTL: settings.cache_ttl_seconds (default 3600)
    │
    ▼
    Return QueryResponse to client
```

**Note on `context_max_tokens`**: The `context_builder.py` module (`build_context_window()`) exists and is importable, but the current `query.py` pipeline passes all reranked chunks directly to `generate_answer()` without calling `build_context_window()`. The `build_context()` function in `prompt_builder.py` formats all chunks without a token budget. The `context_max_tokens` setting (default 4000) is available for future use.

---

## 4. Query Intelligence

**Why it exists**: Legal queries frequently follow exact citation patterns — "Section 302 IPC" or "IPC Section 499". These are *direct lookups*, not similarity searches. Running embeddings + vector search for a query that has a deterministic answer wastes latency, money, and risks retrieval noise.

**Implementation** in `retrieval/query_intelligence.py`:

```python
# Canonical act code map (keys uppercased before lookup)
_ACT_CODE_MAP = {
    "IPC": "ipc", "CRPC": "crpc", "CPC": "cpc", "BNS": "bns",
    "IEA": "iea", "HMA": "hma", "IDA": "ida", "MVA": "mva", "NIA": "nia",
}

# Pattern 1: "Section 120A IPC" / "section 376 of CrPC"
_PATTERN_SECTION_FIRST = re.compile(
    r"[Ss]ection\s+(\d+[A-Za-z]*)\s+(?:of\s+)?({abbrevs})\b",
    re.IGNORECASE,
)

# Pattern 2: "IPC 302" / "BNS Section 103" / "CrPC section 190"
_PATTERN_ACT_FIRST = re.compile(
    r"\b({abbrevs})\s+(?:[Ss]ection\s+)?(\d+[A-Za-z]*)\b",
    re.IGNORECASE,
)
```

`parse_query()` returns:
```python
{"direct_lookup": True,  "act_code": "ipc",  "section_number": "300"}  # direct
{"direct_lookup": False, "act_code": None,   "section_number": None}   # semantic
```

When `direct_lookup=True`:
1. `get_section(act_code, section_number, session)` — single ORM SELECT
2. Skips embedding, vector search, FTS, RRF, and reranking entirely
3. Goes straight to `generate_answer()`

**Direct lookups are NOT cached** — a single indexed DB lookup is faster than a Redis round-trip.

---

## 5. Hybrid Retrieval (Vector + FTS + RRF)

**Why hybrid**: Pure vector search misses exact statutory language ("grievous hurt", "Section 302"). Pure keyword search misses semantic equivalence ("killing someone" → Section 300 IPC). Combining both with RRF outperforms either alone.

### Vector Retrieval (`vector_store/store.py: similarity_search()`)

```sql
SELECT id, act_code, act_name, act_year, chapter_number, chapter_title,
       section_number, section_title, content, type, source_url, token_count,
       embedding, created_at
FROM sections
WHERE (act_code = ANY(:codes) OR :codes IS NULL)
  AND embedding <=> CAST(:vec AS vector) < :max_dist   -- 0.75 threshold
ORDER BY embedding <=> CAST(:vec AS vector)
LIMIT :k
```

- **Model**: `text-embedding-3-small` (1536 dimensions)
- **Index**: IVFFlat with `lists=100`, `vector_cosine_ops`
- **Threshold**: cosine distance < 0.75 — out-of-domain queries return 0 results
- **Candidates**: `top_k_retrieval × 2` (default: 10 × 2 = 20)

### Keyword Retrieval (`vector_store/store.py: fts_search()`)

```sql
SELECT ... FROM sections
WHERE (act_code = ANY(:codes) OR :codes IS NULL)
  AND fts_vector @@ plainto_tsquery('english', :query)
LIMIT :k
```

The `fts_vector` column is `GENERATED ALWAYS AS` (computed, stored):
```sql
setweight(to_tsvector('english', coalesce(section_title, '')), 'A') ||
setweight(to_tsvector('english', coalesce(act_name, '')),      'B') ||
setweight(to_tsvector('english', coalesce(content, '')),       'C')
```

- Weight A (section_title) > Weight B (act_name) > Weight C (content)
- GIN index (`idx_sections_fts`) makes this O(log n)
- Uses `plainto_tsquery` (not `to_tsquery`) — handles natural language without requiring `&` operators

### Reciprocal Rank Fusion (`retrieval/hybrid.py: _reciprocal_rank_fusion()`)

```python
_RRF_K = 60

def _reciprocal_rank_fusion(result_lists, k=_RRF_K):
    scores = {}
    chunks_by_id = {}
    for ranked_list in result_lists:
        for rank, chunk in enumerate(ranked_list, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
            chunks_by_id.setdefault(chunk.id, chunk)
    return sorted([(chunks_by_id[cid], score) for cid, score in scores.items()],
                  key=lambda t: t[1], reverse=True)
```

- `k=60` — standard smoothing constant; reduces over-weighting of top-1 results
- A chunk ranked #1 in both lists: `1/61 + 1/61 = 0.0328`
- A chunk ranked #1 in one list only: `1/61 = 0.0164`
- Deduplicates by chunk ID; keeps first-seen `LegalChunk` object

---

## 6. Reranking

After RRF, `rerank_chunks()` in `retrieval/reranker.py` re-orders results by legal relevance.

**Why a second LLM call?** RRF is statistical — it doesn't understand legal semantics. A question about "bail conditions" might retrieve sections about "bail" (correct) and sections that mention "conditions" in a different context (noise). The reranker uses gpt-4o-mini to re-score by relevance.

**Prompt format**:
```
Query: {query}

Chunks (index, section, content):
0: [Sec 300, ipc] Except in the cases hereinafter excepted...
1: [Sec 299, ipc] Whoever causes death by doing an act...
...

Return ONLY a JSON array of indices ordered by legal relevance (most relevant first), e.g. [2,0,1].
```

**Failure handling**: Any exception (timeout, malformed JSON, rate limit) is caught, logged as `rerank_failed`, and the original RRF order is returned. The user always gets a response.

**Parameters**: `temperature=0.0`, `max_tokens=256`, same model as LLM (`settings.llm_model`).

---

## 7. Context Building & Token Budget

`llm/context_builder.py` provides `build_context_window()` for token-budget-aware chunk selection:

```python
_ENCODER = tiktoken.get_encoding("cl100k_base")

def build_context_window(chunks, max_tokens=4000):
    selected, total = [], 0
    for chunk in chunks:
        block = f"[Section {chunk.section_number} — {chunk.act_name} ({chunk.act_year})]\n{chunk.content}"
        tokens = len(_ENCODER.encode(block))
        if total + tokens > max_tokens:
            break
        selected.append(chunk)
        total += tokens
    return selected
```

The actual context format used by `prompt_builder.py: build_context()` is:
```
[Section {section_number} — {act_name} ({act_year})]
{content}
```

This format is chosen deliberately — it matches the citation format the LLM is instructed to use (`[Section X, Act Name]`), making citation extraction reliable.

---

## 8. LLM Layer & Anti-Hallucination

**The problem**: LLMs are trained on legal text and will confidently generate plausible-sounding but incorrect legal information. For a legal research tool, this is unacceptable.

**The solution**: A 5-rule system prompt that constrains the model to context-only answers.

```
You are a precise legal research assistant for Indian law. You MUST follow these rules:
1. Answer ONLY using the legal text provided in the context below.
   Do NOT use any external knowledge.
2. Every answer MUST include citations in the format [Section X, Act Name].
3. If the answer cannot be found in the provided context, respond exactly:
   "I cannot find this information in the provided legal texts."
4. Do not summarize or paraphrase law; quote the relevant text directly.
5. Preserve legal precision — do not interpret beyond what is written.
```

**Configuration** (from `config.py`):
- `llm_model`: `gpt-4o-mini` (default)
- `llm_temperature`: `0.0` (fully deterministic)
- `llm_max_tokens`: `1000` (response budget; `generate_answer()` uses `1024`)
- `openai_base_url`: `https://api.openai.com/v1` (override to use OpenRouter)

**Citation extraction** (`llm/client.py: _parse_citations()`):
```python
_CITATION_RE = re.compile(r"\[Section\s+([\dA-Za-z]+)\s*,\s*([^\]]+)\]", re.IGNORECASE)
```
Matches `[Section 302, Indian Penal Code]` → `Citation(act_code="ipc", section_number="302", ...)`.
The `act_code` is resolved by finding the matching chunk in the retrieved list.

**Out-of-domain guard**: If `hybrid_retrieve()` returns `[]` (both vector and FTS returned nothing, or all vector results exceeded the 0.75 cosine threshold), `generate_answer()` is still called but with an empty chunk list — the system prompt rule 3 ensures the LLM responds with the standard "cannot find" message.

---

## 9. Caching Architecture

Redis serves two distinct purposes:

| db | Purpose | TTL | Key Pattern |
|---|---|---|---|
| 0 | Query result cache | `cache_ttl_seconds` (3600s) | `query:{sha256hex}` |
| 1 | Celery task broker | — | Celery internals |
| 2 | Celery task results | — | Celery internals |

### Query Cache Key (`cache/query_cache.py`)

```python
def cache_key(query: str, act_codes: list[str] | None) -> str:
    parts = query.strip().lower() + "|" + ",".join(sorted(act_codes or []))
    return "query:" + hashlib.sha256(parts.encode()).hexdigest()
```

- Query is stripped and lowercased for case-insensitive hits
- Act codes are sorted so `["ipc", "crpc"]` and `["crpc", "ipc"]` produce the same key
- Full `QueryResponse` is serialized via `model_dump_json()` and stored as a Redis string

### What IS and ISN'T cached

| Query Type | Cached? | Reason |
|---|---|---|
| Semantic (vector+FTS) | ✅ Yes | Expensive — embedding + 2 DB queries + 2 LLM calls |
| Direct lookup | ❌ No | Single indexed DB lookup — faster than Redis round-trip |
| `use_cache=False` requests | ❌ No | Explicit opt-out (used by evaluation runner) |

### Redis Eviction Policy

Redis is configured with `--maxmemory-policy allkeys-lru`. When memory is full, the least-recently-used keys are evicted automatically. This means the cache is self-managing — no manual TTL tuning needed for memory pressure.

---

## 10. Database Schema

### `sections` table (`infra/postgres/init.sql`)

```sql
CREATE TABLE sections (
    id              TEXT PRIMARY KEY,       -- e.g. "ipc-300-section"
    act_code        TEXT NOT NULL,          -- e.g. "ipc"
    act_name        TEXT NOT NULL,          -- e.g. "Indian Penal Code"
    act_year        TEXT NOT NULL,          -- e.g. "1860" (stored as TEXT)
    chapter_number  TEXT,
    chapter_title   TEXT,
    section_number  TEXT NOT NULL,          -- e.g. "300", "120A"
    section_title   TEXT,
    content         TEXT NOT NULL,
    type            TEXT NOT NULL DEFAULT 'section',  -- section | explanation | clause | amendment
    source_url      TEXT,
    embedding       vector(1536),           -- pgvector, text-embedding-3-small
    fts_vector      tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(section_title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(act_name, '')),      'B') ||
        setweight(to_tsvector('english', coalesce(content, '')),       'C')
    ) STORED,
    token_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

**Key design notes**:
- `act_year` is `TEXT` (not `INTEGER`) — matches the JSON source format and `LegalChunk.act_year: str`
- `type` column (not `chunk_type`) — the ORM maps `SectionEmbedding.type` to `ChunkType` enum
- `fts_vector` is `GENERATED ALWAYS AS ... STORED` — PostgreSQL auto-updates it on INSERT/UPDATE; never write it from Python

**ID format**: `{act_code}-{section_number}-{chunk_type.value}`
- Primary section: `ipc-300-section`
- Explanation sub-chunk: `ipc-300-explanation-0`, `ipc-300-explanation-1`

### Indexes

```sql
-- Act-scoped queries
CREATE INDEX idx_sections_act_code ON sections(act_code);

-- Direct lookup: "Section 120A IPC" → act_code + section_number
CREATE INDEX idx_sections_section_number ON sections(act_code, section_number);

-- Full-text search (FTS leg of hybrid retrieval)
CREATE INDEX idx_sections_fts ON sections USING GIN(fts_vector);

-- Vector ANN search (vector leg of hybrid retrieval)
CREATE INDEX idx_sections_embedding
    ON sections USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

**Why IVFFlat lists=100?** Rule of thumb: `lists ≈ √(row_count)`. With ~2,300 rows, `√2300 ≈ 48`, but 100 provides headroom as the corpus grows. Too few lists = slow (scans too many clusters). Too many = slow (index overhead). 100 is a safe conservative choice.

### `query_logs` table

```sql
CREATE TABLE query_logs (
    id                   BIGSERIAL PRIMARY KEY,
    query_text           TEXT NOT NULL,
    query_hash           VARCHAR(64),
    retrieved_section_ids TEXT[],
    latency_ms           INTEGER,
    cache_hit            BOOLEAN DEFAULT FALSE,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_query_logs_created_at ON query_logs(created_at DESC);
CREATE INDEX idx_query_logs_hash ON query_logs(query_hash);
```

> **Note**: `query_logs` is defined in `init.sql` for observability. The current `query.py` route does not yet write to this table — it is available for future instrumentation.

---

## 11. Ingestion Pipeline

Ingestion is asynchronous via Celery. The pipeline uses a two-task architecture:

```
scripts/ingest.py --act ipc
    │
    │   list_available_acts()  ← ingestion/loader.py
    │   Scans legal-acts/ for subdirectories
    │
    ▼
batch_index_act.delay("ipc")   ← workers/batch_index_task.py
    │
    │   load_act_sections("ipc")  ← ingestion/loader.py
    │   Reads legal-acts/ipc/json/sections/*.json
    │   Each file is one section dict
    │
    │   chunk_section(section)  ← ingestion/chunker.py
    │   → [LegalChunk(type=SECTION), LegalChunk(type=EXPLANATION), ...]
    │
    │   Celery group:
    │   group(embed_and_index_chunk.s(chunk.model_dump()) for chunk in all_chunks)
    │
    ▼
embed_and_index_chunk(chunk_dict)  ← workers/embed_task.py
    │   (runs concurrently for all chunks in the group)
    │
    │   embed_texts([chunk.content], settings)
    │   → 1536-dim vector via text-embedding-3-small
    │   Retry: 3 attempts, 5s delay, time_limit=60s
    │
    │   upsert_chunk(enriched, session)  ← vector_store/store.py
    │   INSERT ... ON CONFLICT DO UPDATE
    │
    ▼
PostgreSQL sections table
```

**Data directory structure**:
```
legal-acts/
└── {act_code}/
    ├── json/
    │   ├── act.json          # Act-level metadata
    │   ├── chapters.json     # Chapter list
    │   └── sections/
    │       ├── section-1.json
    │       ├── section-2.json
    │       └── ...           # One JSON file per section
    └── markdown/             # Human-readable source (not used by ingestion)
```

See [ingestion.md](ingestion.md) for full details including JSON section format and how to add a new act.

---

## 12. Observability

| Signal | Where | How |
|---|---|---|
| Structured logs | stdout | `structlog` — human-readable in dev, JSON lines in production |
| Request latency | structlog | `LatencyLoggingMiddleware` logs every request: method, path, status, latency_ms |
| Query logs | `query_logs` table | Available for SQL analytics (not yet written by current pipeline) |
| Health check | `GET /health` | Returns DB + Redis + OpenAI connectivity status |
| Prometheus metrics | `GET /metrics/` | `prometheus_client.generate_latest()` — plaintext Prometheus format |
| Worker logs | Celery stdout | `batch_index_dispatched`, `chunk_indexed`, `embed_task_failed` |

**Health check response**:
```json
{
  "status": "ok",
  "db": true,
  "redis": true,
  "openai": true
}
```
Status is `"degraded"` if any of the three checks fail.

**Prometheus metrics** (`GET /metrics/`) returns standard Prometheus plaintext — scrape with Prometheus or view with `curl http://localhost:8000/metrics/`.

**Debugging slow queries**:
```sql
SELECT query_text, latency_ms, cache_hit, retrieved_section_ids
FROM query_logs
ORDER BY created_at DESC
LIMIT 20;
```

---

## 13. Key Numbers at a Glance

| Metric | Value | Source |
|---|---|---|
| Acts indexed | 9 | `legal-acts/` subdirectories |
| Total sections | ~2,284 | Evaluation context |
| Embedding dimensions | 1536 | `text-embedding-3-small` |
| Cosine distance threshold | 0.75 | `vector_store/store.py: similarity_search()` |
| IVFFlat lists | 100 | `infra/postgres/init.sql` |
| RRF k parameter | 60 | `retrieval/hybrid.py: _RRF_K` |
| Context token budget | 4,000 | `config.py: context_max_tokens` |
| LLM temperature | 0.0 | `config.py: llm_temperature` |
| LLM max tokens (answer) | 1,024 | `llm/client.py: generate_answer()` |
| Cache TTL | 3,600 seconds | `config.py: cache_ttl_seconds` |
| DB pool size | 10 (max_overflow=20) | `vector_store/database.py: get_engine()` |
| Celery concurrency | 4 workers | `infra/docker-compose.yml` |
| Embed task retries | 3 (5s delay, 60s limit) | `workers/embed_task.py` |
| Embedding batch size | 100 | `config.py: embedding_batch_size` |
| Evaluation pass rate | 100% (12/12) | `eval_report.json` |
| MRR (evaluation) | 0.833 | `eval_report.json` |
| Recall@5 (evaluation) | 0.814 | `eval_report.json` |
| Legal Accuracy (evaluation) | 0.703 | `eval_report.json` |
