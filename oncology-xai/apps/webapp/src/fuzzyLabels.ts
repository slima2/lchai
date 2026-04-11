/**
 * Fuzzy linguistic labels for XAI components.
 *
 * Triangular/trapezoidal membership functions map continuous numeric values
 * to human-readable labels with a degree of membership µ ∈ [0,1].
 * The winning label (highest µ) is displayed in the UI and injected into
 * LLM prompts, ensuring deterministic, controllable explanations that
 * cannot be hallucinated by the language model.
 *
 * All thresholds are editable via the Admin → Fuzzy Labels panel.
 */

/* ═══════════════════════════════════════════════════════════════
   STORAGE: persisted in localStorage, overridable at runtime
   ═══════════════════════════════════════════════════════════════ */

const STORAGE_KEY = 'lchai_fuzzy_label_config';

export interface TrapezoidalMF {
  /** Label shown in the UI */
  label: string;
  /** CSS colour class or hex for visual badge */
  color: string;
  /** Trapezoidal corners [a, b, c, d]: µ=0 at a, µ=1 from b to c, µ=0 at d */
  abcd: [number, number, number, number];
}

export interface FuzzyScale {
  id: string;
  name: string;
  description: string;
  unit: string;
  sets: TrapezoidalMF[];
}

/* ─────────────────── default scales ─────────────────── */

const DEFAULT_INTERACTION_SCALE: FuzzyScale = {
  id: 'interaction_index',
  name: 'Interaction Index |I_jk|',
  description: 'Magnitude of Choquet pairwise interaction indices (absolute value).',
  unit: '|I_jk|',
  sets: [
    { label: 'Negligible',   color: '#9ca3af', abcd: [0, 0, 0.003, 0.008] },
    { label: 'Weak',         color: '#60a5fa', abcd: [0.005, 0.008, 0.012, 0.020] },
    { label: 'Moderate',     color: '#fbbf24', abcd: [0.015, 0.025, 0.035, 0.050] },
    { label: 'Strong',       color: '#f97316', abcd: [0.040, 0.055, 0.070, 0.090] },
    { label: 'Very Strong',  color: '#ef4444', abcd: [0.075, 0.090, 1, 1] },
  ],
};

const DEFAULT_SHAPLEY_PROFILE_SCALE: FuzzyScale = {
  id: 'shapley_profile',
  name: 'Shapley Profile (spread)',
  description: 'Spread = max(φ_k) − min(φ_k). Measures differentiation of singleton Shapley values.',
  unit: 'spread',
  sets: [
    { label: 'Uniform',                  color: '#9ca3af', abcd: [0, 0, 0.003, 0.008] },
    { label: 'Near-Uniform',             color: '#60a5fa', abcd: [0.005, 0.008, 0.015, 0.025] },
    { label: 'Moderately Differentiated', color: '#fbbf24', abcd: [0.020, 0.035, 0.050, 0.070] },
    { label: 'Strongly Differentiated',   color: '#f97316', abcd: [0.060, 0.080, 0.120, 0.160] },
    { label: 'Highly Polarised',          color: '#ef4444', abcd: [0.140, 0.180, 1, 1] },
  ],
};

const DEFAULT_SHAP_BALANCE_SCALE: FuzzyScale = {
  id: 'shap_balance',
  name: 'SHAP Balance (pattern %)',
  description: 'Pattern contribution percentage in SHAP decomposition (embedding + pattern = 100%).',
  unit: 'pat_%',
  sets: [
    { label: 'Embedding-Dominated', color: '#3b82f6', abcd: [0, 0, 5, 12] },
    { label: 'Embedding-Led',       color: '#60a5fa', abcd: [8, 15, 20, 30] },
    { label: 'Balanced',            color: '#a855f7', abcd: [25, 35, 45, 55] },
    { label: 'Pattern-Led',         color: '#f97316', abcd: [45, 55, 65, 75] },
    { label: 'Pattern-Dominated',   color: '#ef4444', abcd: [70, 80, 100, 100] },
  ],
};

const DEFAULT_SHAPLEY_INDIVIDUAL_SCALE: FuzzyScale = {
  id: 'shapley_individual',
  name: 'Shapley Individual (δ% from uniform)',
  description: 'Per-pattern deviation from uniform importance: δ = (φ_k − 1/n) / (1/n) × 100%.',
  unit: 'δ%',
  sets: [
    { label: 'Average',          color: '#9ca3af', abcd: [0, 0, 2, 5] },
    { label: 'Slightly Above',   color: '#60a5fa', abcd: [3, 6, 10, 15] },
    { label: 'Moderately Above', color: '#fbbf24', abcd: [12, 20, 30, 40] },
    { label: 'Strongly Above',   color: '#f97316', abcd: [35, 50, 100, 100] },
  ],
};

const DEFAULT_ATTENTION_LEVEL_SCALE: FuzzyScale = {
  id: 'attention_level',
  name: 'ABMIL Attention Level (percentile)',
  description: 'Tile attention percentile from gated ABMIL. Higher = model focuses more on this tile.',
  unit: 'percentile',
  sets: [
    { label: 'Very Low Attention',  color: '#9ca3af', abcd: [0, 0, 20, 40] },
    { label: 'Low Attention',       color: '#60a5fa', abcd: [30, 45, 55, 65] },
    { label: 'Moderate Attention',  color: '#fbbf24', abcd: [55, 65, 75, 85] },
    { label: 'High Attention',      color: '#f97316', abcd: [75, 85, 92, 97] },
    { label: 'Very High Attention', color: '#ef4444', abcd: [93, 97, 100, 100] },
  ],
};

export const ALL_DEFAULT_SCALES: FuzzyScale[] = [
  DEFAULT_INTERACTION_SCALE,
  DEFAULT_SHAPLEY_PROFILE_SCALE,
  DEFAULT_SHAP_BALANCE_SCALE,
  DEFAULT_SHAPLEY_INDIVIDUAL_SCALE,
  DEFAULT_ATTENTION_LEVEL_SCALE,
];

/* ═══════════════════════════════════════════════════════════════
   CONFIG MANAGEMENT
   ═══════════════════════════════════════════════════════════════ */

function loadConfig(): FuzzyScale[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as FuzzyScale[];
  } catch { /* corrupt → reset */ }
  return ALL_DEFAULT_SCALES;
}

export function saveConfig(scales: FuzzyScale[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(scales));
}

export function resetConfig(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function getScales(): FuzzyScale[] {
  return loadConfig();
}

export function getScale(id: string): FuzzyScale {
  const scales = loadConfig();
  return scales.find((s) => s.id === id) || ALL_DEFAULT_SCALES.find((s) => s.id === id)!;
}

/* ═══════════════════════════════════════════════════════════════
   MEMBERSHIP & CLASSIFICATION
   ═══════════════════════════════════════════════════════════════ */

function trapezoidalMu(x: number, [a, b, c, d]: [number, number, number, number]): number {
  if (x <= a || x >= d) return 0;
  if (x >= b && x <= c) return 1;
  if (x < b) return (x - a) / (b - a);
  return (d - x) / (d - c);
}

export interface FuzzyResult {
  label: string;
  color: string;
  mu: number;
  allMemberships: { label: string; mu: number; color: string }[];
}

export function classify(value: number, scaleId: string): FuzzyResult {
  const scale = getScale(scaleId);
  const memberships = scale.sets.map((s) => ({
    label: s.label,
    color: s.color,
    mu: trapezoidalMu(value, s.abcd),
  }));

  const best = memberships.reduce((a, b) => (b.mu > a.mu ? b : a), memberships[0]);
  return { label: best.label, color: best.color, mu: best.mu, allMemberships: memberships };
}

/* ═══════════════════════════════════════════════════════════════
   HIGH-LEVEL CLASSIFIERS
   ═══════════════════════════════════════════════════════════════ */

export function classifyInteraction(value: number): FuzzyResult & { direction: 'Synergy' | 'Redundancy' } {
  const result = classify(Math.abs(value), 'interaction_index');
  return { ...result, direction: value >= 0 ? 'Synergy' : 'Redundancy' };
}

export function classifyShapleyProfile(shapleyValues: Record<string, number>): FuzzyResult {
  const vals = Object.values(shapleyValues).filter((v) => typeof v === 'number');
  if (vals.length === 0) return { label: 'Unknown', color: '#9ca3af', mu: 0, allMemberships: [] };
  const spread = Math.max(...vals) - Math.min(...vals);
  return classify(spread, 'shapley_profile');
}

export function classifyShapleyIndividual(phi: number, n: number): FuzzyResult & { direction: 'above' | 'below' | 'at' } {
  const uniform = 1 / n;
  const deltaPct = Math.abs((phi - uniform) / uniform) * 100;
  const result = classify(deltaPct, 'shapley_individual');
  const direction = deltaPct < 2 ? 'at' as const : phi > uniform ? 'above' as const : 'below' as const;
  return { ...result, direction };
}

export function classifySHAPBalance(patternPct: number): FuzzyResult {
  return classify(patternPct, 'shap_balance');
}

export function classifyAttention(percentile: number): FuzzyResult {
  return classify(percentile, 'attention_level');
}

/* ═══════════════════════════════════════════════════════════════
   PROMPT HELPERS (inject into LLM prompts for determinism)
   ═══════════════════════════════════════════════════════════════ */

export function shapleyProfilePromptFragment(shapleyValues: Record<string, number>): string {
  const profile = classifyShapleyProfile(shapleyValues);
  const n = Object.keys(shapleyValues).length;
  const uniform = (1 / n).toFixed(4);
  const vals = Object.values(shapleyValues);
  const spread = (Math.max(...vals) - Math.min(...vals)).toFixed(4);

  const perPattern = Object.entries(shapleyValues)
    .sort(([, a], [, b]) => b - a)
    .map(([p, v]) => {
      const ind = classifyShapleyIndividual(v, n);
      return `  ${p}: ${v.toFixed(4)} → ${ind.label} (${ind.direction} average)`;
    })
    .join('\n');

  return `SHAPLEY PROFILE CLASSIFICATION (fuzzy logic — system-controlled, not hallucinated):
Profile: "${profile.label}" (spread=${spread}, uniform=${uniform})
Per-pattern:
${perPattern}
Use these exact labels in your explanation. Do NOT invent different intensity words.`;
}

export function interactionPromptFragment(interactions: Record<string, number>): string {
  const lines = Object.entries(interactions)
    .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
    .slice(0, 6)
    .map(([pair, val]) => {
      const c = classifyInteraction(val);
      return `  ${pair.replace('_', ' × ')}: ${val > 0 ? '+' : ''}${val.toFixed(4)} → "${c.label} ${c.direction}"`;
    })
    .join('\n');

  return `INTERACTION INDEX CLASSIFICATION (fuzzy logic — system-controlled):
${lines}
Use these exact labels. A "Negligible" interaction means the pair provides no meaningful joint signal. A "Moderate Synergy" means co-presence adds predictive value beyond individual contributions.`;
}

export function shapBalancePromptFragment(patternPct: number): string {
  const c = classifySHAPBalance(patternPct);
  return `SHAP BALANCE CLASSIFICATION (fuzzy logic — system-controlled):
Pattern contribution: ${patternPct.toFixed(1)}% → "${c.label}"
Use this exact label. "Embedding-Dominated" means patterns are nearly irrelevant; "Pattern-Led" means patterns are the primary signal source.`;
}
