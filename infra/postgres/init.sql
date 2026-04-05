-- LexGrid PostgreSQL Initialization Script
-- Enables pgvector and pg_trgm extensions, creates core tables + indexes

-- Enable pgvector extension for 1536-dim OpenAI embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable trigram extension for full-text search similarity
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Legal sections table with vector embeddings
-- Stores parsed chunks from Indian Bare Acts dataset
-- NOTE: table name is "sections" to match the SQLAlchemy ORM __tablename__
CREATE TABLE IF NOT EXISTS sections (
    id TEXT PRIMARY KEY,
    act_code TEXT NOT NULL,
    act_name TEXT NOT NULL,
    act_year TEXT NOT NULL,
    chapter_number TEXT,
    chapter_title TEXT,
    section_number TEXT NOT NULL,
    section_title TEXT,
    content TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'section',
    source_url TEXT,
    embedding vector(1536),
    fts_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(section_title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(act_name, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'C')
    ) STORED,
    token_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index on act_code for fast act-scoped lookups
CREATE INDEX IF NOT EXISTS idx_sections_act_code
    ON sections(act_code);

-- Composite index for direct section lookup (act_code + section_number)
-- Supports query-intelligence path: "Section 120A IPC" → DB lookup
CREATE INDEX IF NOT EXISTS idx_sections_section_number
    ON sections(act_code, section_number);

-- GIN index on tsvector column for full-text search (FTS leg of hybrid retrieval)
CREATE INDEX IF NOT EXISTS idx_sections_fts
    ON sections USING GIN(fts_vector);

-- IVFFlat index on embedding column for approximate nearest-neighbour vector search
-- lists=100 is a good baseline for ~2,300 rows; tune up when corpus grows
CREATE INDEX IF NOT EXISTS idx_sections_embedding
    ON sections
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Query metrics table for observability and cache-hit tracking
CREATE TABLE IF NOT EXISTS query_logs (
    id BIGSERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64),
    retrieved_section_ids TEXT[],
    latency_ms INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for time-range queries on query_logs (used by metrics/dashboard)
CREATE INDEX IF NOT EXISTS idx_query_logs_created_at
    ON query_logs(created_at DESC);

-- Index for cache-deduplication lookups by query hash
CREATE INDEX IF NOT EXISTS idx_query_logs_hash
    ON query_logs(query_hash);
