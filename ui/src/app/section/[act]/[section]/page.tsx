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
    <div className="flex h-screen bg-dark-surface text-warm-silver font-sans overflow-hidden">
      {/* Sidebar strip — matches app shell */}
      <aside className="w-[220px] shrink-0 bg-dark-surface border-r border-dark-border flex flex-col">
        <div className="px-4 py-5 border-b border-dark-border">
          <a href="/" className="text-base font-bold text-ivory tracking-tight hover:text-terracotta transition-colors">
            LexGrid
          </a>
          <p className="text-[10px] text-stone-gray mt-0.5 uppercase tracking-widest">Legal Research</p>
        </div>
        <nav className="flex-1 px-3 py-4">
          <a
            href="/"
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-warm-silver hover:bg-dark-elevated hover:text-ivory transition-colors"
          >
            ← Back to Chat
          </a>
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto bg-parchment">
        <div className="max-w-3xl mx-auto px-6 py-10 space-y-4">
          {/* Breadcrumb */}
          <nav className="text-xs font-sans text-olive-gray">
            <a href="/" className="hover:text-terracotta transition-colors">Home</a>
            <span className="mx-1">›</span>
            <span className="uppercase">{normalizedActLabel}</span>
            <span className="mx-1">›</span>
            <span>Section {normalizedSectionLabel}</span>
          </nav>

          <SectionViewer section={result} />
        </div>
      </main>
    </div>
  );
}
