'use client';

/**
 * ResultCard — renders a full QueryResponse:
 *   - Answer text in legal serif font
 *   - Citation badges
 *   - Performance metrics + cache indicator
 */

import type { QueryResponse } from '@/lib/types';
import CitationBadge from '@/components/CitationBadge';
import { Zap } from 'lucide-react';

interface Props {
  response: QueryResponse;
}

export default function ResultCard({ response }: Props) {
  const retrievalMs = response.retrieval_ms ?? 0;
  const totalMs = response.total_ms ?? response.latency_ms ?? 0;
  const chunksRetrieved = response.chunks_retrieved ?? response.retrieved_chunks.length;

  return (
    <article className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm space-y-4">
      {/* Answer */}
      <div className="font-serif leading-relaxed text-lg text-ink whitespace-pre-wrap">
        {response.answer}
      </div>

      {/* Citations */}
      {response.citations.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-sans font-semibold text-gray-500 uppercase tracking-wide">
            Citations
          </p>
          <div className="flex flex-wrap gap-2">
            {response.citations.map((c, i) => (
              <CitationBadge key={`${c.act_code}-${c.section_number}-${i}`} citation={c} />
            ))}
          </div>
        </div>
      )}

      {/* Performance footer */}
      <p className="text-xs text-gray-400 font-sans flex items-center gap-1">
        {chunksRetrieved} sections retrieved
        {retrievalMs > 0 && ` · ${retrievalMs.toFixed(0)}ms retrieval`}
        {totalMs > 0 && ` · ${totalMs.toFixed(0)}ms total`}
        {response.cache_hit && (
          <span className="ml-1 inline-flex items-center gap-0.5 text-amber-600">
            <Zap className="w-3 h-3" />
            cached
          </span>
        )}
      </p>
    </article>
  );
}
