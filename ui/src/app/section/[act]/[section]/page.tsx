/**
 * Direct section lookup page — /section/[act]/[section]
 * Calls GET /search and renders SectionViewer or a 404 state.
 */

import { notFound } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
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
    <div className="flex h-full">
      {/* Sidebar — hidden on mobile, matches app Sidebar exactly */}
      <aside className="hidden md:flex w-[220px] flex-shrink-0 bg-ink flex-col h-full">
        <div className="px-4 py-4 border-b border-dark-surface flex-shrink-0">
          <p className="font-serif text-[15px] font-medium text-ivory">LexGrid</p>
          <p className="font-sans text-[11px] text-olive-gray mt-0.5">Indian Legal Research</p>
        </div>
        <nav className="flex-1 px-3 py-4">
          <a
            href="/"
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-warm-silver hover:bg-dark-surface hover:text-ivory transition-colors font-sans"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Chat
          </a>
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
        {/* Mobile header — matches MobileHeader pattern */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 bg-ink border-b border-dark-surface flex-shrink-0">
          <a
            href="/"
            className="flex items-center justify-center w-8 h-8 text-warm-silver hover:text-ivory transition-colors"
            aria-label="Back to chat"
          >
            <ArrowLeft className="w-4 h-4" />
          </a>
          <span className="font-serif text-[15px] font-medium text-ivory">LexGrid</span>
        </header>

        <main className="flex-1 overflow-y-auto bg-parchment">
          <div className="max-w-3xl mx-auto px-4 md:px-6 py-8 md:py-10 space-y-4">
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
    </div>
  );
}
