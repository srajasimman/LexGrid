/**
 * Shared TypeScript types mirroring the backend Pydantic models.
 * Keep in sync with backend/app/models/*.py.
 */

export interface Citation {
  act_code: string;
  act_name: string;
  section_number: string;
  section_title?: string | null;
  source_url?: string | null;
}

export interface RetrievedChunk {
  id: string;
  act_code: string;
  act_name: string;
  section_number: string;
  section_title?: string | null;
  content: string;
  score: number;
  retrieval_method: 'vector' | 'keyword' | 'hybrid';
}

export interface QueryRequest {
  query: string;
  act_filter?: string | null;
  top_k?: number;
  use_cache?: boolean;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  retrieved_chunks: RetrievedChunk[];
  query: string;
  cache_hit: boolean;
  latency_ms: number;
  retrieval_ms?: number;
  total_ms?: number;
  chunks_retrieved?: number;
}

export interface SearchRequest {
  act_code: string;
  section_number: string;
}

export interface SectionResult {
  id: string;
  act_code: string;
  act_name: string;
  act_year?: string | null;
  section_number: string;
  section_title?: string | null;
  chapter_number?: string | null;
  chapter_title?: string | null;
  content: string;
  source_url?: string | null;
  relevance_score?: number | null;
}

export interface SearchResponse {
  results: SectionResult[];
  total: number;
}

export interface SectionSourceResponse {
  act_code: string;
  section_number: string;
  normalized_section_number: string;
  source_markdown_found: boolean;
  source_markdown?: string | null;
  source_markdown_path?: string | null;
}

export interface HealthStatus {
  status: string;
  database: string;
  redis: string;
  version: string;
}
