export const DEFAULT_AI_RESILIENCE_THRESHOLD = 40;

export interface AIResilienceModifierState {
  threshold: number;
  hide_flagged: boolean;
}

export const DEFAULT_AI_RESILIENCE_MODIFIER_STATE: AIResilienceModifierState = {
  threshold: DEFAULT_AI_RESILIENCE_THRESHOLD,
  hide_flagged: false,
};

export function normalizeAIResilienceThreshold(value: unknown): number {
  if (value == null) return DEFAULT_AI_RESILIENCE_THRESHOLD;
  if (typeof value === "string" && !value.trim()) return DEFAULT_AI_RESILIENCE_THRESHOLD;
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return DEFAULT_AI_RESILIENCE_THRESHOLD;
  return Math.max(0, Math.min(100, Math.round(numeric)));
}

export function normalizeAIResilienceModifierState(
  value: Partial<AIResilienceModifierState> = {},
): AIResilienceModifierState {
  return {
    threshold: normalizeAIResilienceThreshold(
      value.threshold ?? DEFAULT_AI_RESILIENCE_MODIFIER_STATE.threshold,
    ),
    hide_flagged: Boolean(value.hide_flagged),
  };
}

export function normalizeAIResilienceScore(value: unknown): number | null {
  if (value == null) return null;
  if (typeof value === "string" && !value.trim()) return null;
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return null;
  return Math.max(0, Math.min(100, numeric));
}

export function isAIResilienceScoreFlagged(
  score: unknown,
  thresholdOrState: number | AIResilienceModifierState = DEFAULT_AI_RESILIENCE_THRESHOLD,
): boolean {
  const normalizedScore = normalizeAIResilienceScore(score);
  if (normalizedScore == null) return false;
  const threshold =
    typeof thresholdOrState === "number"
      ? normalizeAIResilienceThreshold(thresholdOrState)
      : normalizeAIResilienceThreshold(thresholdOrState.threshold);
  return normalizedScore < threshold;
}

export function filterAIResilienceFlagged<T>(
  items: T[],
  getScore: (item: T) => unknown,
  state: AIResilienceModifierState,
): T[] {
  if (!state.hide_flagged) return items;
  return items.filter((item) => !isAIResilienceScoreFlagged(getScore(item), state));
}

export function toAIResilienceFilterPayload(state: AIResilienceModifierState): {
  ai_resilience_filter: boolean;
} {
  return {
    ai_resilience_filter: state.hide_flagged,
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function readScoreFromRecord(record: Record<string, unknown>): number | null {
  const direct = normalizeAIResilienceScore(record.ai_resilience_score ?? record.ai_resilience);
  if (direct != null) return direct;

  const scores = asRecord(record.scores);
  const scoreValue = normalizeAIResilienceScore(scores.ai_resilience ?? scores.ai_resilience_score);
  if (scoreValue != null) return scoreValue;

  const v2Scores = asRecord(record.v2_scores);
  const v2Value = normalizeAIResilienceScore(v2Scores.ai_resilience ?? v2Scores.ai_resilience_score);
  if (v2Value != null) return v2Value;

  const evidence = asRecord(record.evidence);
  const evidenceValue = normalizeAIResilienceScore(
    evidence.ai_resilience_score ?? evidence.ai_resilience,
  );
  if (evidenceValue != null) return evidenceValue;

  const strategyEvidence = asRecord(record.strategy_evidence);
  return normalizeAIResilienceScore(
    strategyEvidence.ai_resilience_score ?? strategyEvidence.ai_resilience,
  );
}

export function readAIResilienceScore(value: unknown): number | null {
  return readScoreFromRecord(asRecord(value));
}
