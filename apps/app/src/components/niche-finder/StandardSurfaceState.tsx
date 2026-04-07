interface StandardSurfaceStateProps {
  loading: boolean;
  error: string | null;
}

export default function StandardSurfaceState({
  loading,
  error,
}: StandardSurfaceStateProps) {
  if (loading) {
    return (
      <div className="rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4 text-sm text-[var(--color-text-muted)]">
        Calculating niche score...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-[var(--color-negative)]/40 bg-[var(--color-dark-card)] p-4 text-sm text-[var(--color-negative)]">
        {error}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4 text-sm text-[var(--color-text-muted)]">
      Enter a city and service to generate an opportunity score.
    </div>
  );
}
