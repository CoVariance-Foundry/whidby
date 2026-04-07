import type { EvidenceRecord } from "@/lib/niche-finder/exploration-types";
import EvidenceMissingState from "@/components/niche-finder/EvidenceMissingState";

interface EvidencePanelProps {
  evidence: EvidenceRecord[];
}

export default function EvidencePanel({ evidence }: EvidencePanelProps) {
  return (
    <section className="rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4">
      <h2 className="text-sm font-semibold">Score-Driving Evidence</h2>
      <div className="mt-3 space-y-3">
        {evidence.map((item) =>
          item.isAvailable ? (
            <div
              key={`${item.category}-${item.label}`}
              className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark)] p-3"
            >
              <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                {item.category}
              </p>
              <p className="mt-1 text-sm text-[var(--color-text-primary)]">{item.label}</p>
              <p className="text-sm text-[var(--color-accent)]">{String(item.value)}</p>
              <p className="mt-1 text-xs text-[var(--color-text-muted)]">{item.source}</p>
            </div>
          ) : (
            <EvidenceMissingState key={`${item.category}-${item.label}`} category={item.category} />
          )
        )}
      </div>
    </section>
  );
}
