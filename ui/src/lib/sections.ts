/**
 * Section normalization helpers for route-safe citation links.
 */

export function normalizeSectionRouteParam(sectionNumber: string): string {
  const noPrefix = sectionNumber.replace(/^section\s+/i, '').trim();
  const alnumOnly = noPrefix.replace(/[^a-zA-Z0-9]/g, '');
  if (!alnumOnly) {
    return '';
  }

  if (/^\d+$/.test(alnumOnly)) {
    return alnumOnly;
  }

  const match = /^(\d+)([a-zA-Z]+)$/.exec(alnumOnly);
  if (match) {
    const [, prefix, suffix] = match;
    return `${prefix}${suffix.toUpperCase()}`;
  }

  return alnumOnly.toUpperCase();
}

export function normalizeActCodeLabel(actCode: string): string {
  return actCode.trim().toUpperCase();
}
