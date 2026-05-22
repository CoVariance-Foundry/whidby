export type TokenSet = {
  text: string;
  background: string;
  bar: string;
  border: string;
};

export type ScoreToneKey = "high" | "good" | "warning" | "danger" | "muted";

export type ScoreTone = TokenSet & {
  key: ScoreToneKey;
};

export type StrategyAccentId =
  | "easy_win"
  | "cash_cow"
  | "blue_ocean"
  | "expand_conquer"
  | "portfolio_builder"
  | "seasonal_arbitrage"
  | "gbp_blitz"
  | "keyword_hijack";

export type StrategyAccent = TokenSet & {
  accent_id: StrategyAccentId;
};

const scoreTones = {
  high: {
    key: "high",
    text: "var(--score-high)",
    background: "var(--score-high-soft)",
    bar: "var(--score-high)",
    border: "var(--score-high-border)",
  },
  good: {
    key: "good",
    text: "var(--score-good)",
    background: "var(--score-good-soft)",
    bar: "var(--score-good)",
    border: "var(--score-good-border)",
  },
  warning: {
    key: "warning",
    text: "var(--score-warning)",
    background: "var(--score-warning-soft)",
    bar: "var(--score-warning)",
    border: "var(--score-warning-border)",
  },
  danger: {
    key: "danger",
    text: "var(--score-danger)",
    background: "var(--score-danger-soft)",
    bar: "var(--score-danger)",
    border: "var(--score-danger-border)",
  },
  muted: {
    key: "muted",
    text: "var(--score-muted)",
    background: "var(--score-muted-soft)",
    bar: "var(--score-muted)",
    border: "var(--score-muted-border)",
  },
} as const satisfies Record<ScoreToneKey, ScoreTone>;

const strategyAccentIds = [
  "easy_win",
  "cash_cow",
  "blue_ocean",
  "expand_conquer",
  "portfolio_builder",
  "seasonal_arbitrage",
  "gbp_blitz",
  "keyword_hijack",
] as const satisfies StrategyAccentId[];

const strategyAccents = Object.fromEntries(
  strategyAccentIds.map((accentId) => [
    accentId,
    {
      accent_id: accentId,
      text: `var(--strategy-${accentId.replaceAll("_", "-")})`,
      background: `var(--strategy-${accentId.replaceAll("_", "-")}-soft)`,
      bar: `var(--strategy-${accentId.replaceAll("_", "-")})`,
      border: `var(--strategy-${accentId.replaceAll("_", "-")}-border)`,
    },
  ]),
) as Record<StrategyAccentId, StrategyAccent>;

const fallbackStrategyAccent = strategyAccents.easy_win;

export function scoreToneForValue(value: number | null | undefined): ScoreTone {
  if (typeof value !== "number" || !Number.isFinite(value)) return scoreTones.muted;
  if (value >= 80) return scoreTones.high;
  if (value >= 60) return scoreTones.good;
  if (value >= 40) return scoreTones.warning;
  return scoreTones.danger;
}

export function strategyAccentForId(strategyId: string | null | undefined): StrategyAccent {
  const normalized = strategyId?.trim().toLowerCase();
  if (!normalized) return fallbackStrategyAccent;
  return strategyAccents[normalized as StrategyAccentId] ?? fallbackStrategyAccent;
}

