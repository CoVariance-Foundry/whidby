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
      <div
        role="status"
        aria-live="polite"
        data-testid="surface-loading"
        className="rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4 text-sm text-[var(--color-text-muted)]"
      >
        Running live scoring pipeline — this takes up to a minute on first run.
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        data-testid="surface-error"
        className="rounded-lg border border-[var(--color-negative)]/40 bg-[var(--color-dark-card)] p-4 text-sm text-[var(--color-negative)]"
      >
        {error}
      </div>
    );
  }

  return (
    <div data-testid="surface-empty" className="rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4 text-sm text-[var(--color-text-muted)]">
      Enter a city and service to generate an opportunity score.
    </div>
  );
}
