'use client';

/**
 * SearchBar — natural language query input with two modes:
 *   "ask"    → free-text legal question
 *   "lookup" → act code + section number direct lookup
 */

import { Search } from 'lucide-react';
import { useState, type FormEvent } from 'react';

const ACT_CODES = ['bns', 'cpc', 'crpc', 'hma', 'ida', 'iea', 'ipc', 'mva', 'nia'];

interface Props {
  onSubmit: (query: string, actCodes: string[]) => void;
  isLoading: boolean;
  selectedActCodes?: string[];
}

export default function SearchBar({ onSubmit, isLoading, selectedActCodes = [] }: Props) {
  const [mode, setMode] = useState<'ask' | 'lookup'>('ask');
  const [query, setQuery] = useState('');
  const [actCode, setActCode] = useState('ipc');
  const [sectionNum, setSectionNum] = useState('');

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (mode === 'ask') {
      if (!query.trim()) return;
      onSubmit(query.trim(), selectedActCodes);
    } else {
      if (!sectionNum.trim()) return;
      onSubmit(`Section ${sectionNum.trim()} ${actCode.toUpperCase()}`, [actCode]);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-3">
      {/* Mode toggle */}
      <div className="flex gap-2 text-sm">
        {(['ask', 'lookup'] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`px-3 py-1 rounded-full border transition-colors ${
              mode === m
                ? 'bg-amber-800 text-white border-amber-800'
                : 'bg-white text-ink border-gray-300 hover:border-amber-700'
            }`}
          >
            {m === 'ask' ? 'Ask a question' : 'Look up section'}
          </button>
        ))}
      </div>

      {mode === 'ask' ? (
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. What is criminal conspiracy under IPC?"
              className="w-full pl-9 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-700 bg-white text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="px-5 py-2.5 bg-amber-800 text-white rounded-lg text-sm font-medium hover:bg-amber-900 disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Searching…' : 'Search'}
          </button>
        </div>
      ) : (
        <div className="flex gap-2 items-center">
          <select
            value={actCode}
            onChange={(e) => setActCode(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-700"
          >
            {ACT_CODES.map((c) => (
              <option key={c} value={c}>{c.toUpperCase()}</option>
            ))}
          </select>
          <input
            type="text"
            value={sectionNum}
            onChange={(e) => setSectionNum(e.target.value)}
            placeholder="Section number, e.g. 120A"
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-700"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="px-5 py-2.5 bg-amber-800 text-white rounded-lg text-sm font-medium hover:bg-amber-900 disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Looking up…' : 'Look up'}
          </button>
        </div>
      )}
    </form>
  );
}
