# LexGrid Ingestion

> This document covers the full ingestion pipeline — how legal act data is structured on disk, how it flows through the chunker and Celery workers into pgvector, and how to add a new act.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Data Directory Structure](#2-data-directory-structure)
3. [Section JSON Format](#3-section-json-format)
4. [Chunking Logic](#4-chunking-logic)
5. [Celery Task Architecture](#5-celery-task-architecture)
6. [Running Ingestion](#6-running-ingestion)
7. [How to Add a New Act](#7-how-to-add-a-new-act)
8. [Re-ingestion & Idempotency](#8-re-ingestion--idempotency)
9. [Monitoring Ingestion](#9-monitoring-ingestion)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Overview

Ingestion converts raw legal act JSON files into embedded vector chunks stored in PostgreSQL. The pipeline is:

```
legal-acts/{act}/json/sections/*.json
    │
    ▼  ingestion/loader.py
load_act_sections(act_code)
    │  Reads all section-*.json files for the act
    │
    ▼  ingestion/chunker.py
chunk_section(section_dict)
    │  Produces 1–N LegalChunk objects per section
    │  (1 SECTION chunk + 0–N EXPLANATION chunks)
    │
    ▼  workers/batch_index_task.py
batch_index_act(act_code)  [Celery task]
    │  Dispatches a Celery group of embed tasks
    │
    ▼  workers/embed_task.py
embed_and_index_chunk(chunk_dict)  [Celery task, runs concurrently]
    │  embed_texts([chunk.content], settings)
    │  → 1536-dim vector via text-embedding-3-small
    │
    ▼  vector_store/store.py
upsert_chunk(enriched, session)
    │  INSERT ... ON CONFLICT DO UPDATE
    │
    ▼
PostgreSQL sections table
```

---

## 2. Data Directory Structure

```
legal-acts/
└── {act_code}/
    ├── json/
    │   ├── act.json          # Act-level metadata (not used by ingestion)
    │   ├── chapters.json     # Chapter list (not used by ingestion)
    │   └── sections/
    │       ├── section-1.json
    │       ├── section-2.json
    │       ├── section-10.json
    │       ├── section-120A.json
    │       └── ...           # One JSON file per section
    └── markdown/             # Human-readable source (not used by ingestion)
```

The loader (`ingestion/loader.py: load_act_sections()`) reads all `*.json` files from `legal-acts/{act_code}/json/sections/` in sorted order. Files are sorted lexicographically by filename.

**Currently indexed acts**:
```
legal-acts/
├── bns/    # Bharatiya Nyaya Sanhita (2023)
├── cpc/    # Code of Civil Procedure (1908)
├── crpc/   # Code of Criminal Procedure (1973)
├── hma/    # Hindu Marriage Act (1955)
├── ida/    # Indian Divorce Act (1869)
├── iea/    # Indian Evidence Act (1872)
├── ipc/    # Indian Penal Code (1860)
├── mva/    # Motor Vehicles Act (1988)
└── nia/    # National Investigation Agency Act (2008)
```

---

## 3. Section JSON Format

Each section file contains a single JSON object. Here is the complete format with all fields:

```json
{
  "section_number": "300",
  "section_title": "Murder",
  "file_id": "section-300",
  "chapter_number": "16",
  "chapter_title": "Of Offences Affecting Life",
  "act_code": "ipc",
  "act_name": "Indian Penal Code",
  "act_year": "1860",
  "text": "Except in the cases hereinafter excepted, culpable homicide is murder...",
  "explanations": [
    "Explanation 1.— A person is said to commit 'culpable homicide'..."
  ],
  "amendments": [],
  "source_url": "https://devgan.in/ipc/chapter_16.php"
}
```

### Field Reference

| Field | Type | Required | Used by chunker | Description |
|---|---|---|---|---|
| `section_number` | `string` | ✅ | ✅ | Section number, e.g. `"300"`, `"120A"` |
| `section_title` | `string` | ❌ | ✅ | Section title, e.g. `"Murder"` |
| `file_id` | `string` | ❌ | ❌ | Filename without extension (informational) |
| `chapter_number` | `string` | ❌ | ✅ | Chapter number, e.g. `"16"` |
| `chapter_title` | `string` | ❌ | ✅ | Chapter title |
| `act_code` | `string` | ✅ | ✅ | Lowercase act code, e.g. `"ipc"` |
| `act_name` | `string` | ✅ | ✅ | Full act name, e.g. `"Indian Penal Code"` |
| `act_year` | `string` | ✅ | ✅ | Year as **string**, e.g. `"1860"` (not integer) |
| `text` | `string` | ✅ | ✅ | Full section text — **required, non-empty** |
| `explanations` | `string[]` | ❌ | ✅ | List of explanation strings — each becomes a separate chunk |
| `amendments` | `any[]` | ❌ | ❌ | Not used by current chunker |
| `source_url` | `string` | ❌ | ✅ | Source URL for citations |

> **Critical**: `act_year` must be a **string** (e.g. `"1860"`), not an integer. `LegalChunk.act_year` is typed as `str`. Pydantic will coerce integers to strings, but be explicit.

> **Critical**: Sections with empty `text` are silently skipped by the chunker. Always provide non-empty `text`.

---

## 4. Chunking Logic

The chunker (`ingestion/chunker.py`) converts one section dict into 1–N `LegalChunk` objects.

### Primary Chunk (SECTION)

One `SECTION` chunk is created per section:

```python
LegalChunk(
    id=f"{act_code}-{section_number}-section",   # e.g. "ipc-300-section"
    act_code=act_code,
    act_name=section.get("act_name", ""),
    act_year=str(section.get("act_year", "")),
    chapter_number=section.get("chapter_number"),
    chapter_title=section.get("chapter_title"),
    section_number=section_number,
    section_title=section.get("section_title"),
    content=section.get("text", "").strip(),      # uses "text" field
    chunk_type=ChunkType.SECTION,
    source_url=section.get("source_url"),
    token_count=count_tokens(content),            # tiktoken cl100k_base
)
```

### Explanation Chunks (EXPLANATION)

One `EXPLANATION` chunk is created per non-empty explanation string:

```python
LegalChunk(
    id=f"{act_code}-{section_number}-explanation-{idx}",  # e.g. "ipc-300-explanation-0"
    content=f"Explanation to Section {section_number}: {explanation_text}",
    chunk_type=ChunkType.EXPLANATION,
    # ... same act/chapter/section metadata as primary chunk
)
```

### Chunk ID Format

| Chunk Type | ID Format | Example |
|---|---|---|
| SECTION | `{act_code}-{section_number}-section` | `ipc-300-section` |
| EXPLANATION | `{act_code}-{section_number}-explanation-{idx}` | `ipc-300-explanation-0` |

The `idx` is 0-based, matching the position in the `explanations` array.

### Token Counting

Token counts are computed using `tiktoken.get_encoding("cl100k_base")` — the same encoding used by `text-embedding-3-small` and `gpt-4o-mini`. The `token_count` field is stored in the database for observability but is not used in retrieval logic.

---

## 5. Celery Task Architecture

Ingestion uses a two-task architecture to maximise parallelism:

### Task 1: `batch_index_act` (`workers/batch_index_task.py`)

```python
@celery_app.task
def batch_index_act(act_code: str) -> dict:
    sections = load_act_sections(act_code)
    all_chunks = [chunk for section in sections for chunk in chunk_section(section)]
    task_group = group(embed_and_index_chunk.s(chunk.model_dump()) for chunk in all_chunks)
    task_group.delay()
    return {"act_code": act_code, "sections_count": len(sections), "chunks_count": len(all_chunks)}
```

This task:
1. Loads all section JSON files for the act
2. Chunks them into `LegalChunk` objects
3. Dispatches a **Celery group** — all `embed_and_index_chunk` tasks run concurrently

### Task 2: `embed_and_index_chunk` (`workers/embed_task.py`)

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=5, time_limit=60, soft_time_limit=45)
def embed_and_index_chunk(self, chunk_dict: dict) -> bool:
    async def _run():
        chunk = LegalChunk.model_validate(chunk_dict)
        embeddings = await embed_texts([chunk.content], settings)
        enriched = LegalChunkWithEmbedding(**chunk.model_dump(), embedding=embeddings[0])
        async with factory() as session:
            await upsert_chunk(enriched, session)
            await session.commit()
        return True
    return asyncio.run(_run())
```

This task:
1. Deserializes the `LegalChunk` from the dict
2. Calls `embed_texts()` — one OpenAI embedding API call per chunk
3. Upserts the chunk + embedding into PostgreSQL
4. Retries up to 3 times on failure (5s delay, 60s hard time limit)

### Why Two Tasks?

`batch_index_act` is a **fan-out** task — it does the cheap work (loading, chunking) synchronously and then fans out to N parallel `embed_and_index_chunk` tasks. This means:
- All chunks for an act are embedded concurrently (up to `concurrency=4` workers)
- Each embed task is independently retryable
- A single failed embed doesn't block the rest of the act

### Celery Configuration (`workers/celery_app.py`)

```python
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # fetch one task at a time — prevents hoarding
)
celery_app.autodiscover_tasks(["app.workers"])
```

`worker_prefetch_multiplier=1` is critical for embed tasks — without it, a single worker could grab all tasks from the queue, preventing other workers from helping.

---

## 6. Running Ingestion

### Prerequisites

1. PostgreSQL and Redis must be running
2. The Celery worker must be running
3. `OPENAI_API_KEY` must be set (for embedding generation)
4. `LEGAL_ACTS_DIR` must point to the `legal-acts/` directory

### Ingest All Acts

```bash
# From repo root
python scripts/ingest.py --act all
```

Output:
```
Discovered 9 act(s): bns, cpc, crpc, hma, ida, iea, ipc, mva, nia
Dispatched bns
Dispatched cpc
Dispatched crpc
...
Dispatched nia

All tasks dispatched. Monitor with:
  celery -A app.workers.celery_app flower
```

### Ingest Specific Acts

```bash
# Single act
python scripts/ingest.py --act ipc

# Multiple acts (comma-separated)
python scripts/ingest.py --act ipc,crpc,bns
```

### Inside Docker

```bash
# Run ingestion inside the celery-worker container
docker compose exec celery-worker python scripts/ingest.py --act all

# Or the backend container
docker compose exec backend python scripts/ingest.py --act all
```

---

## 7. How to Add a New Act

### Step 1: Create the Directory Structure

```bash
mkdir -p legal-acts/{act_code}/json/sections
```

### Step 2: Create Section JSON Files

Create one JSON file per section in `legal-acts/{act_code}/json/sections/`:

```bash
# File naming convention: section-{section_number}.json
legal-acts/xyz/json/sections/section-1.json
legal-acts/xyz/json/sections/section-2.json
legal-acts/xyz/json/sections/section-10.json
```

Each file must follow the [Section JSON Format](#3-section-json-format):

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
  "text": "This Act may be called the Example Act, 2024. It shall come into force on such date as the Central Government may, by notification in the Official Gazette, appoint.",
  "explanations": [],
  "amendments": [],
  "source_url": "https://example.com/xyz/section/1"
}
```

### Step 3: Register in Query Intelligence

Edit `backend/app/retrieval/query_intelligence.py`:

```python
_ACT_CODE_MAP: dict[str, str] = {
    "IPC": "ipc",
    "CRPC": "crpc",
    # ... existing entries ...
    "XYZ": "xyz",   # add this line
}
```

The regex patterns are built dynamically from `_ACT_CODE_MAP.keys()` — no other changes needed.

### Step 4: Run Ingestion

```bash
python scripts/ingest.py --act xyz
```

### Step 5: Verify

```bash
# Check section count
psql -U lexgrid -d lexgrid -c \
  "SELECT COUNT(*) FROM sections WHERE act_code = 'xyz';"

# Check embeddings
psql -U lexgrid -d lexgrid -c \
  "SELECT COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS with_embeddings,
          COUNT(*) AS total
   FROM sections WHERE act_code = 'xyz';"

# Test a query
curl -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "short title of xyz act", "act_filter": "xyz"}'

# Test direct lookup
curl -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "XYZ Section 1"}'
```

---

## 8. Re-ingestion & Idempotency

Ingestion is **fully idempotent** — you can re-run it safely at any time.

The upsert uses PostgreSQL's `ON CONFLICT DO UPDATE`:

```python
stmt = (
    insert(SectionEmbedding)
    .values(**values)
    .on_conflict_do_update(index_elements=["id"], set_=values)
)
```

This means:
- If a section already exists, it is updated with the new content and embedding
- If it doesn't exist, it is inserted
- No duplicates are created

**When to re-ingest**:
- After changing `EMBEDDING_MODEL` (embeddings are in a different vector space)
- After updating section JSON files (content changes)
- After adding new sections to an existing act
- After a failed ingestion (safe to retry)

---

## 9. Monitoring Ingestion

### Celery Flower (Web UI)

```bash
pip install flower
celery -A app.workers.celery_app flower
# Open http://localhost:5555
```

Flower shows:
- Active, queued, and completed tasks
- Task success/failure rates
- Worker status and concurrency

### Celery CLI

```bash
# Inspect active tasks
celery -A app.workers.celery_app inspect active

# Inspect registered tasks
celery -A app.workers.celery_app inspect registered

# Check worker stats
celery -A app.workers.celery_app inspect stats
```

### Database Queries

```sql
-- Section counts per act
SELECT act_code,
       COUNT(*) AS total_chunks,
       COUNT(*) FILTER (WHERE type = 'section') AS sections,
       COUNT(*) FILTER (WHERE type = 'explanation') AS explanations,
       COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS with_embeddings,
       COUNT(*) FILTER (WHERE embedding IS NULL) AS missing_embeddings
FROM sections
GROUP BY act_code
ORDER BY act_code;

-- Total indexed
SELECT COUNT(*) AS total_sections FROM sections WHERE embedding IS NOT NULL;

-- Recently ingested (last 10 minutes)
SELECT act_code, section_number, section_title, created_at
FROM sections
WHERE created_at > NOW() - INTERVAL '10 minutes'
ORDER BY created_at DESC
LIMIT 20;
```

### Structlog Output

The Celery worker emits structured log events:

```
# batch_index_task.py
{"event": "batch_index_dispatched", "act_code": "ipc", "sections_count": 511, "chunks_count": 623}

# embed_task.py
{"event": "chunk_indexed", "chunk_id": "ipc-300-section"}
{"event": "embed_task_failed", "chunk_id": "ipc-300-section", "error": "RateLimitError: ..."}

# pipeline.py
{"event": "act_ingested", "act_code": "ipc", "section_count": 511, "chunk_count": 623}
{"event": "pipeline_complete", "act_count": 9, "total_chunks": 2847}
```

---

## 10. Troubleshooting

### Sections Missing Embeddings

**Symptom**: `COUNT(*) FILTER (WHERE embedding IS NULL) > 0`

**Cause**: `embed_and_index_chunk` tasks failed (rate limit, timeout, API error).

**Fix**:
1. Check Celery logs for `embed_task_failed` events
2. Re-run ingestion for the affected act — upsert is idempotent:
   ```bash
   python scripts/ingest.py --act ipc
   ```
3. If rate-limited, reduce `EMBEDDING_BATCH_SIZE` or add delay between batches

### `FileNotFoundError: Sections directory not found`

**Symptom**: `FileNotFoundError: Sections directory not found for act 'xyz': /app/legal-acts/xyz/json/sections`

**Cause**: The sections directory doesn't exist or `LEGAL_ACTS_DIR` points to the wrong path.

**Fix**:
```bash
# Check the path
ls legal-acts/xyz/json/sections/

# Check the env var
echo $LEGAL_ACTS_DIR

# In Docker, verify the volume mount
docker compose exec backend ls /app/legal-acts/
```

### Celery Tasks Not Processing

**Symptom**: Tasks are dispatched but never complete.

**Cause**: Celery worker is not running, or is connected to the wrong Redis database.

**Fix**:
```bash
# Check worker is running
docker compose ps celery-worker

# Check broker URL
celery -A app.workers.celery_app inspect ping

# Restart worker
docker compose restart celery-worker
```

### `ModuleNotFoundError: No module named 'app'`

**Symptom**: Running `python scripts/ingest.py` fails with import error.

**Cause**: Running from the wrong directory, or `PYTHONPATH` not set.

**Fix**: Run from the repo root (the script adds `backend/` to `sys.path` automatically):
```bash
# ✅ Correct — from repo root
python scripts/ingest.py --act ipc

# ❌ Wrong — from scripts/ directory
cd scripts && python ingest.py
```

### IVFFlat Index Degraded After Bulk Ingest

**Symptom**: Vector search returns poor results after a large ingestion.

**Cause**: PostgreSQL statistics are stale; the query planner may not use the IVFFlat index optimally.

**Fix**:
```bash
psql -U lexgrid -d lexgrid -c "ANALYZE sections;"
```

For very large ingestions (10,000+ rows), also consider rebuilding the index:
```sql
REINDEX INDEX idx_sections_embedding;
```
