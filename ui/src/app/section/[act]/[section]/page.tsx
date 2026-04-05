/**
 * Direct section lookup page — /section/[act]/[section]
 * Calls GET /search and renders SectionViewer or a 404 state.
 */

import { notFound } from 'next/navigation';
import SectionViewer from '@/components/SectionViewer';
import { searchSection } from '@/lib/api';
import { normalizeActCodeLabel, normalizeSectionRouteParam } from '@/lib/sections';

interface PageProps {
  params: { act: string; section: string };
}

export default async function SectionPage({ params }: PageProps) {
  const { act, section } = params;
  let data;

  try {
    data = await searchSection(act, section);
  } catch {
    notFound();
  }

  if (!data || data.results.length === 0) {
    notFound();
  }

  const result = data.results[0];
  const normalizedActLabel = normalizeActCodeLabel(act);
  const normalizedSectionLabel = normalizeSectionRouteParam(section) || result.section_number;

  return (
    <main className="min-h-screen bg-parchment">
      <header className="border-b border-gray-200 bg-white px-4 py-5 sm:px-8">
        <a href="/" className="text-xl font-sans font-bold text-amber-800 tracking-tight">
          LexGrid
        </a>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-10 sm:px-8 space-y-4">
        <nav className="text-xs font-sans text-gray-400">
          <a href="/" className="hover:text-amber-800">Home</a>
          <span className="mx-1">›</span>
          <span className="uppercase">{normalizedActLabel}</span>
          <span className="mx-1">›</span>
          <span>Section {normalizedSectionLabel}</span>
        </nav>

        <SectionViewer section={result} />
      </div>
    </main>
  );
}
