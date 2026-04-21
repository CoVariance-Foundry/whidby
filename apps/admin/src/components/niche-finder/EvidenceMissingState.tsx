interface EvidenceMissingStateProps {
  category: string;
}

export default function EvidenceMissingState({ category }: EvidenceMissingStateProps) {
  return (
    <div className="rounded-md border border-dashed border-[var(--color-dark-border)] bg-[var(--color-dark)] p-3 text-sm text-[var(--color-text-muted)]">
      Evidence for <span className="font-medium">{category}</span> is currently unavailable.
    </div>
  );
}
