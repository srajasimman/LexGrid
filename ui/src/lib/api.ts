/**
 * Typed API client — wraps all backend endpoints with axios.
 * Base URL is driven by NEXT_PUBLIC_API_URL (falls back to localhost:8000).
 */

import axios from 'axios';
import type {
  HealthStatus,
  QueryRequest,
  QueryResponse,
  SectionSourceResponse,
  SearchResponse,
} from '@/lib/types';

function resolveApiBaseUrl(): string {
  const isServer = typeof window === 'undefined';

  if (isServer) {
    return (
      process.env.BACKEND_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      'http://localhost:8000'
    );
  }

  return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
}

const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  headers: { 'Content-Type': 'application/json' },
});

/**
 * POST /query — run a natural-language legal query through the RAG pipeline.
 */
export async function queryLegal(req: QueryRequest): Promise<QueryResponse> {
  const { data } = await api.post<QueryResponse>('/query', req);
  return data;
}

/**
 * GET /search — retrieve a specific section by act code + section number.
 */
export async function searchSection(
  act_code: string,
  section_number: string,
): Promise<SearchResponse> {
  const { data } = await api.get<SearchResponse>('/search', {
    params: { act_code, section_number },
  });
  return data;
}

/**
 * GET /source — retrieve canonical markdown source by act + section.
 */
export async function getSectionSource(
  act_code: string,
  section_number: string,
): Promise<SectionSourceResponse> {
  const { data } = await api.get<SectionSourceResponse>('/source', {
    params: { act_code, section_number },
  });
  return data;
}

/**
 * GET /health — check API health and dependency status.
 */
export async function getHealth(): Promise<HealthStatus> {
  const { data } = await api.get<HealthStatus>('/health');
  return data;
}
