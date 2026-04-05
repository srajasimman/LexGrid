# LexGrid API Reference

> All endpoints are served by the FastAPI backend at `http://localhost:8000` (default).
> Interactive documentation is available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`.

---

## Table of Contents

1. [Base URL & Headers](#1-base-url--headers)
2. [POST /query/](#2-post-query)
3. [GET /search/](#3-get-search)
4. [GET /health](#4-get-health)
5. [GET /metrics/](#5-get-metrics)
6. [Data Models](#6-data-models)
7. [Error Responses](#7-error-responses)
8. [Act Codes Reference](#8-act-codes-reference)

---

## 1. Base URL & Headers

```
Base URL: http://localhost:8000
```

All request bodies must use `Content-Type: application/json`.

CORS is enabled for all origins (`allow_origins=["*"]`) — the API is accessible from any frontend.

---

## 2. POST /query/

The main RAG endpoint. Accepts a natural-language legal question and returns a grounded answer with citations.

> ⚠️ **Trailing slash required**: `POST /query/` — not `/query`. FastAPI redirects `/query` → `/query/` with a 307, which `httpx` will not follow for POST requests.

### Request

```
POST /query/
Content-Type: application/json
```

**Body** (`QueryRequest`):

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| `query` | `string` | ✅ | — | 3–2000 chars | The legal question |
| `act_filter` | `string \| null` | ❌ | `null` | Valid act code | Filter results to one act |
| `top_k` | `integer` | ❌ | `5` | 1–20 | Number of chunks to retrieve |
| `use_cache` | `boolean` | ❌ | `true` | — | Whether to use Redis cache |

**Example request**:
```bash
curl -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the punishment for murder under IPC?",
    "act_filter": "ipc",
    "top_k": 5,
    "use_cache": true
  }'
```

**Direct lookup example** (bypasses embedding + vector search):
```bash
curl -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Section 300 IPC?"}'
```

### Response

**200 OK** (`QueryResponse`):

| Field | Type | Description |
|---|---|---|
| `answer` | `string` | Grounded legal answer from the LLM |
| `citations` | `Citation[]` | Structured citations extracted from the answer |
| `retrieved_chunks` | `RetrievedChunk[]` | Chunks used as context (truncated to 500 chars each) |
| `query` | `string` | The original query string |
| `cache_hit` | `boolean` | Whether this response was served from Redis cache |
| `latency_ms` | `integer` | Total end-to-end latency in milliseconds |

**Example response**:
```json
{
  "answer": "According to [Section 302, Indian Penal Code], whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.",
  "citations": [
    {
      "act_code": "ipc",
      "act_name": "Indian Penal Code",
      "section_number": "302",
      "section_title": "Punishment of murder",
      "source_url": "https://devgan.in/ipc/chapter_16.php"
    }
  ],
  "retrieved_chunks": [
    {
      "id": "ipc-302-section",
      "act_code": "ipc",
      "act_name": "Indian Penal Code",
      "section_number": "302",
      "section_title": "Punishment of murder",
      "content": "Whoever commits murder shall be punished with death, or...",
      "score": 1.0,
      "retrieval_method": "hybrid"
    }
  ],
  "query": "What is the punishment for murder under IPC?",
  "cache_hit": false,
  "latency_ms": 1243
}
```

**Out-of-domain response** (when no relevant sections found):
```json
{
  "answer": "I cannot find this information in the provided legal texts.",
  "citations": [],
  "retrieved_chunks": [],
  "query": "What is quantum physics?",
  "cache_hit": false,
  "latency_ms": 87
}
```

### Pipeline Behaviour

| Query Pattern | Path | Cached? |
|---|---|---|
| `"Section 300 IPC"` | Direct DB lookup → LLM | ❌ No |
| `"IPC 302"` | Direct DB lookup → LLM | ❌ No |
| `"punishment for murder"` | Embed → Hybrid retrieve → Rerank → LLM | ✅ Yes (if `use_cache=true`) |
| `"quantum physics"` | Embed → Hybrid retrieve → (empty) → LLM | ✅ Yes |

---

## 3. GET /search/

Direct section lookup by `act_code` and `section_number`. No embedding, no LLM — pure database lookup.

> **Use case**: Verify a section is indexed, inspect raw content, or build a section browser UI.

### Request

```
GET /search/?act_code={act_code}&section_number={section_number}
```

**Query parameters**:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `act_code` | `string` | ❌ | Act code, e.g. `ipc` |
| `section_number` | `string` | ❌ | Section number, e.g. `300`, `120A` |

If either parameter is omitted, returns an empty result set.

**Example request**:
```bash
curl "http://localhost:8000/search/?act_code=ipc&section_number=300"
```

### Response

**200 OK** (`SearchResponse`):

| Field | Type | Description |
|---|---|---|
| `results` | `SectionResult[]` | Matching sections (0 or 1 for direct lookup) |
| `total` | `integer` | Number of results |
| `query` | `string \| null` | The search query used |

**Example response** (found):
```json
{
  "results": [
    {
      "id": "ipc-300-section",
      "act_code": "ipc",
      "act_name": "Indian Penal Code",
      "act_year": "1860",
      "chapter_number": "16",
      "chapter_title": "Of Offences Affecting Life",
      "section_number": "300",
      "section_title": "Murder",
      "content": "Except in the cases hereinafter excepted, culpable homicide is murder...",
      "source_url": "https://devgan.in/ipc/chapter_16.php",
      "relevance_score": null
    }
  ],
  "total": 1,
  "query": "ipc 300"
}
```

**Example response** (not found):
```json
{
  "results": [],
  "total": 0,
  "query": "xyz 999"
}
```

---

## 4. GET /health

Returns the health status of all three backend dependencies: PostgreSQL, Redis, and OpenAI.

### Request

```
GET /health
```

No parameters.

```bash
curl http://localhost:8000/health
```

### Response

**200 OK**:

| Field | Type | Description |
|---|---|---|
| `status` | `string` | `"ok"` if all checks pass, `"degraded"` if any fail |
| `db` | `boolean` | PostgreSQL reachable (`SELECT 1` succeeded) |
| `redis` | `boolean` | Redis reachable (`PING` succeeded) |
| `openai` | `boolean` | OpenAI API reachable (test completion with `max_tokens=1`) |

**Example response** (healthy):
```json
{
  "status": "ok",
  "db": true,
  "redis": true,
  "openai": true
}
```

**Example response** (degraded — Redis down):
```json
{
  "status": "degraded",
  "db": true,
  "redis": false,
  "openai": true
}
```

> **Note**: The OpenAI check makes a real API call with `max_tokens=1`. This incurs a small cost and adds ~200–500ms to the health check latency. Use `/health` for monitoring, not high-frequency polling.

---

## 5. GET /metrics/

Returns Prometheus-formatted plaintext metrics for scraping.

### Request

```
GET /metrics/
```

> ⚠️ **Trailing slash required**: `GET /metrics/` — not `/metrics`.

```bash
curl http://localhost:8000/metrics/
```

### Response

**200 OK** — `Content-Type: text/plain; version=0.0.4; charset=utf-8`

Returns standard Prometheus exposition format:

```
# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 1234.0
...
# HELP process_virtual_memory_bytes Virtual memory size in bytes.
# TYPE process_virtual_memory_bytes gauge
process_virtual_memory_bytes 1.23456789e+08
...
```

**Scrape configuration** (Prometheus `prometheus.yml`):
```yaml
scrape_configs:
  - job_name: lexgrid
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics/
```

---

## 6. Data Models

### `QueryRequest`

```typescript
interface QueryRequest {
  query: string;          // 3–2000 chars, required
  act_filter?: string;    // single act code, e.g. "ipc" — null searches all acts
  top_k?: number;         // 1–20, default 5
  use_cache?: boolean;    // default true
}
```

### `QueryResponse`

```typescript
interface QueryResponse {
  answer: string;                    // LLM-generated grounded answer
  citations: Citation[];             // Structured citations from answer text
  retrieved_chunks: RetrievedChunk[]; // Chunks used as context
  query: string;                     // Original query
  cache_hit: boolean;                // true if served from Redis
  latency_ms: number;                // End-to-end latency
}
```

### `Citation`

Extracted from the LLM answer via regex `\[Section\s+([\dA-Za-z]+)\s*,\s*([^\]]+)\]`.

```typescript
interface Citation {
  act_code: string;           // e.g. "ipc"
  act_name: string;           // e.g. "Indian Penal Code" (from LLM answer text)
  section_number: string;     // e.g. "302", "120A"
  section_title?: string;     // e.g. "Punishment of murder" (from matched chunk)
  source_url?: string;        // Source URL (from matched chunk)
}
```

### `RetrievedChunk`

```typescript
interface RetrievedChunk {
  id: string;               // e.g. "ipc-300-section"
  act_code: string;         // e.g. "ipc"
  act_name: string;         // e.g. "Indian Penal Code"
  section_number: string;   // e.g. "300"
  section_title?: string;   // e.g. "Murder"
  content: string;          // Truncated to 500 chars
  score: number;            // Always 1.0 (placeholder — actual scores not exposed)
  retrieval_method: string; // "hybrid" | "direct"
}
```

### `SearchResponse`

```typescript
interface SearchResponse {
  results: SectionResult[];
  total: number;
  query?: string;
}
```

### `SectionResult`

```typescript
interface SectionResult {
  id: string;
  act_code: string;
  act_name: string;
  act_year: string;           // NOTE: string, e.g. "1860"
  chapter_number?: string;
  chapter_title?: string;
  section_number: string;
  section_title?: string;
  content: string;            // Full content (not truncated)
  source_url?: string;
  relevance_score?: number;   // null for direct lookups
}
```

---

## 7. Error Responses

### 422 Unprocessable Entity

Returned when request validation fails (Pydantic validation error).

```bash
# Example: query too short
curl -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "hi"}'
```

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "query"],
      "msg": "String should have at least 3 characters",
      "input": "hi",
      "ctx": {"min_length": 3}
    }
  ]
}
```

Common validation errors:

| Error | Cause | Fix |
|---|---|---|
| `string_too_short` on `query` | Query < 3 chars | Use at least 3 characters |
| `string_too_long` on `query` | Query > 2000 chars | Truncate query |
| `greater_than_equal` on `top_k` | `top_k < 1` | Use `top_k` ≥ 1 |
| `less_than_equal` on `top_k` | `top_k > 20` | Use `top_k` ≤ 20 |

### 307 Temporary Redirect

Returned when the trailing slash is missing on `/query` or `/metrics`.

```bash
# This returns 307 → /query/
curl -X POST http://localhost:8000/query -d '...'
```

**Fix**: Always include the trailing slash: `POST /query/`, `GET /metrics/`.

### 500 Internal Server Error

Returned on unhandled exceptions (database connection failure, OpenAI API error, etc.).

```json
{
  "detail": "Internal Server Error"
}
```

Check the backend logs (`docker compose logs backend`) for the full traceback.

---

## 8. Act Codes Reference

Valid values for `act_filter`:

| Code | Full Name | Year |
|---|---|---|
| `bns` | Bharatiya Nyaya Sanhita | 2023 |
| `cpc` | Code of Civil Procedure | 1908 |
| `crpc` | Code of Criminal Procedure | 1973 |
| `hma` | Hindu Marriage Act | 1955 |
| `ida` | Indian Divorce Act | 1869 |
| `iea` | Indian Evidence Act | 1872 |
| `ipc` | Indian Penal Code | 1860 |
| `mva` | Motor Vehicles Act | 1988 |
| `nia` | National Investigation Agency Act | 2008 |

**Query Intelligence abbreviations** (trigger direct lookup):

| Abbreviation | Maps to |
|---|---|
| `IPC`, `ipc` | `ipc` |
| `CrPC`, `crpc`, `CRPC` | `crpc` |
| `CPC`, `cpc` | `cpc` |
| `BNS`, `bns` | `bns` |
| `IEA`, `iea` | `iea` |
| `HMA`, `hma` | `hma` |
| `IDA`, `ida` | `ida` |
| `MVA`, `mva` | `mva` |
| `NIA`, `nia` | `nia` |

**Direct lookup trigger patterns**:
- `"Section 300 IPC"` → fetches `ipc` section `300`
- `"section 376 of CrPC"` → fetches `crpc` section `376`
- `"IPC 302"` → fetches `ipc` section `302`
- `"BNS Section 103"` → fetches `bns` section `103`
- `"CrPC section 190"` → fetches `crpc` section `190`
