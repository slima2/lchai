/**
 * Canonical six histological patterns and overlay colours (tile ROI palette).
 * Keep in sync with inference `PATTERN_PALETTE` / web overlays.
 */
export const ANORAK_PATTERN_ORDER = [
  'lepidic',
  'acinar',
  'papillary',
  'micropapillary',
  'solid',
  'cribriform',
] as const;

export type AnorakPattern = (typeof ANORAK_PATTERN_ORDER)[number];

export const PATTERN_COLORS: Record<AnorakPattern, string> = {
  lepidic: '#0000FF',
  acinar: '#FF0000',
  papillary: '#FFFF00',
  micropapillary: '#00FF00',
  solid: '#800000',
  cribriform: '#00FFFF',
};

const DISALLOWED = new Set(['mucinous']);

export function isDisallowedPatternName(name: string | null | undefined): boolean {
  return DISALLOWED.has((name || '').toLowerCase());
}

/** Colour for a pattern label; unknown names fall back to neutral grey. */
export function patternColor(pattern: string | null | undefined): string {
  if (!pattern) return '#888888';
  const k = pattern.toLowerCase() as AnorakPattern;
  return PATTERN_COLORS[k] ?? '#888888';
}

export function filterAllowedPatternResults<T extends { pattern?: string }>(
  items: T[] | undefined | null,
): T[] {
  if (!items?.length) return [];
  return items.filter((x) => !isDisallowedPatternName(x.pattern));
}

/** Sort by canonical overlay order (not by percentage). */
export function sortPatternsCanonical<T extends { pattern?: string }>(items: T[]): T[] {
  const order = new Map<string, number>(ANORAK_PATTERN_ORDER.map((p, i) => [p, i]));
  return [...items].sort((a, b) => {
    const ai = order.get((a.pattern || '').toLowerCase()) ?? 999;
    const bi = order.get((b.pattern || '').toLowerCase()) ?? 999;
    return ai - bi;
  });
}

export function predominantPatternForDisplay(
  rawPredominant: string | null | undefined,
  patternResults: { pattern?: string; percentage?: number }[],
): string {
  if (!isDisallowedPatternName(rawPredominant) && rawPredominant) {
    return rawPredominant;
  }
  const allowed = filterAllowedPatternResults(patternResults);
  if (!allowed.length) return '—';
  const top = [...allowed].sort((a, b) => (b.percentage || 0) - (a.percentage || 0))[0];
  return top?.pattern || '—';
}
