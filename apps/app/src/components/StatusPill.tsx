export type ReportStatus = "complete" | "running" | "archived";

const MAP: Record<
  ReportStatus,
  { bg: string; color: string; border: string; label: string }
> = {
  complete: {
    bg: "#e2ede5",
    color: "var(--accent-ink)",
    border: "#c7ddcd",
    label: "Complete",
  },
  running: {
    bg: "var(--warn-soft)",
    color: "var(--warn)",
    border: "#ead7b0",
    label: "Running",
  },
  archived: {
    bg: "var(--paper-alt)",
    color: "var(--ink-3)",
    border: "var(--rule)",
    label: "Archived",
  },
};

export default function StatusPill({ status }: { status: ReportStatus }) {
  const s = MAP[status];
  return (
    <span
      style={{
        fontFamily: "var(--serif)",
        fontStyle: "italic",
        fontSize: 11.5,
        padding: "2px 9px",
        borderRadius: 10,
        background: s.bg,
        color: s.color,
        border: "1px solid " + s.border,
      }}
    >
      {s.label}
    </span>
  );
}
