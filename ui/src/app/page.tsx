'use client';

/**
 * Main search page — integrates SearchBar, FilterPanel (sidebar), and ResultCard.
 * Uses React Query's useMutation to call POST /query.
 */

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import SearchBar from '@/components/SearchBar';
import FilterPanel from '@/components/FilterPanel';
import ResultCard from '@/components/ResultCard';
import { queryLegal } from '@/lib/api';
import type { QueryResponse } from '@/lib/types';

export default function HomePage() {
  const [selectedActs, setSelectedActs] = useState<string[]>([]);

  const mutation = useMutation<QueryResponse, Error, { query: string; acts: string[] }>({
    mutationFn: ({ query, acts }) =>
      queryLegal({
        query,
        act_filter: acts.length === 1 ? acts[0] : undefined,
        top_k: 5,
        use_cache: true,
      }),
  });

  function handleSearch(query: string, actCodes: string[]) {
    mutation.mutate({ query, acts: actCodes });
  }

  return (
    <main className="min-h-screen bg-parchment">
      {/* Hero header */}
      <header className="border-b border-gray-200 bg-white px-4 py-5 sm:px-8">
        <h1 className="text-xl font-sans font-bold text-amber-800 tracking-tight">
          LexGrid
        </h1>
        <p className="text-xs text-gray-500 mt-0.5">
          AI-powered research on Indian Bare Acts
        </p>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8 sm:px-8 lg:flex lg:gap-10">
        {/* Sidebar */}
        <aside className="lg:w-56 shrink-0 mb-6 lg:mb-0">
          <FilterPanel onChange={setSelectedActs} />
        </aside>

        {/* Content */}
        <section className="flex-1 space-y-6">
          <SearchBar
            onSubmit={handleSearch}
            isLoading={mutation.isPending}
            selectedActCodes={selectedActs}
          />

          {mutation.isPending && (
            <p className="text-sm text-gray-400 animate-pulse font-sans">
              Searching legal corpus…
            </p>
          )}

          {mutation.isError && (
            <p className="text-sm text-red-600 font-sans">
              Error: {mutation.error.message}
            </p>
          )}

          {mutation.isSuccess && mutation.data && (
            <ResultCard response={mutation.data} />
          )}
        </section>
      </div>
    </main>
  );
}
