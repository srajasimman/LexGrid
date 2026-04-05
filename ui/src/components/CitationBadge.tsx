'use client';

/**
 * CitationBadge — renders a citation as a clickable amber pill
 * that links to /section/{act_code}/{section_number}.
 */

import Link from 'next/link';
import type { Citation } from '@/lib/types';
import { normalizeSectionRouteParam } from '@/lib/sections';

interface Props {
  citation: Citation;
}

export default function CitationBadge({ citation }: Props) {
  const label = `${citation.act_name} § ${citation.section_number}`;
  const normalizedSection = normalizeSectionRouteParam(citation.section_number);
  const href = `/section/${citation.act_code.toLowerCase()}/${encodeURIComponent(normalizedSection || citation.section_number)}`;

  return (
    <Link
      href={href}
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200 hover:bg-amber-100 transition-colors"
      title={citation.section_title ?? label}
    >
      {label}
    </Link>
  );
}
