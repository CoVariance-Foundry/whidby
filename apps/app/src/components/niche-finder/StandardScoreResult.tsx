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
        <p className="text-3xl font-semibold text-[var(--color-accent)]">
          {result.scoreResult.opportunityScore}
        </p>
        <p className="text-sm text-[var(--color-text-secondary)]">
          {result.scoreResult.classificationLabel} Opportunity
        </p>
      </div>
      <p className="mt-3 text-sm text-[var(--color-text-muted)]">
        Query: {result.query.city} - {result.query.service}
      </p>
    </div>
  );
}
