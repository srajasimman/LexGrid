'use client';

/**
 * SectionViewer — accordion component for a single legal section.
 * Shows act metadata as header; collapses/expands full text.
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import type { SectionResult } from '@/lib/types';

interface Props {
  section: SectionResult;
}

const PREVIEW_LENGTH = 200;

export default function SectionViewer({ section }: Props) {
  const [expanded, setExpanded] = useState(false);
  const isLong = section.content.length > PREVIEW_LENGTH;

  return (
    <article className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      {/* Header */}
      <header className="px-5 py-4 bg-amber-50 border-b border-amber-100">
        <p className="text-xs font-sans font-semibold text-amber-700 uppercase tracking-wide">
          {section.act_name}{section.act_year ? ` ${section.act_year}` : ''}
          {section.chapter_title && ` — ${section.chapter_title}`}
        </p>
        <h2 className="mt-0.5 text-base font-sans font-semibold text-ink">
          Section {section.section_number}
          {section.section_title ? `: ${section.section_title}` : ''}
        </h2>
      </header>

      {/* Body */}
      <div className="px-5 py-4">
        <p className="font-serif leading-relaxed text-ink">
          {expanded || !isLong
            ? section.content
            : `${section.content.slice(0, PREVIEW_LENGTH)}…`}
        </p>

        <div className="mt-3 flex items-center justify-between">
          {isLong && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="flex items-center gap-1 text-sm text-amber-800 hover:text-amber-900 font-sans"
            >
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              {expanded ? 'Collapse' : 'Read full section'}
            </button>
          )}
          {section.source_url && (
            <a
              href={section.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 font-sans ml-auto"
            >
              <ExternalLink className="w-3 h-3" />
              Source
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
