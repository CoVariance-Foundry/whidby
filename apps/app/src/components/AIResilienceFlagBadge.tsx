import {
  DEFAULT_AI_RESILIENCE_THRESHOLD,
  isAIResilienceScoreFlagged,
  normalizeAIResilienceScore,
  normalizeAIResilienceThreshold,
} from "@/lib/ai-resilience-modifier";

export function AIResilienceFlagBadge({
  score,
  threshold = DEFAULT_AI_RESILIENCE_THRESHOLD,
}: {
  score: unknown;
  threshold?: number;
}) {
  const normalizedScore = normalizeAIResilienceScore(score);
  const normalizedThreshold = normalizeAIResilienceThreshold(threshold);
  if (!isAIResilienceScoreFlagged(normalizedScore, normalizedThreshold)) return null;

  return (
    <span
      aria-label={`AI Resilience flagged: score ${Math.round(normalizedScore ?? 0)} below threshold ${normalizedThreshold}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        minHeight: 22,
        padding: "2px 8px",
        borderRadius: 999,
        border: "1px solid var(--rule)",
        background: "var(--warn-soft)",
        color: "var(--warn)",
        fontSize: 11,
        fontWeight: 750,
        lineHeight: 1.4,
      }}
    >
      AI resilience flagged
    </span>
  );
}
