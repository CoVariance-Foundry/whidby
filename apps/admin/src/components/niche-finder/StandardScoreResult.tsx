import type { StandardSurfaceResponse } from "@/lib/niche-finder/types";

interface StandardScoreResultProps {
  result: StandardSurfaceResponse;
}

export default function StandardScoreResult({ result }: StandardScoreResultProps) {
  return (
    <div className="rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4">
      <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
        Standard Niche Score
      </p>
      <div className="mt-2 flex items-end gap-3">
        <p data-testid="standard-score-value" className="text-3xl font-semibold text-[var(--color-accent)]">
          {result.score_result.opportunity_score}
        </p>
        <p data-testid="standard-classification" className="text-sm text-[var(--color-text-secondary)]">
          {result.score_result.classification_label} Opportunity
        </p>
      </div>
      <p className="mt-3 text-sm text-[var(--color-text-muted)]">
        Query: {result.query.city} - {result.query.service}
      </p>
    </div>
  );
}
