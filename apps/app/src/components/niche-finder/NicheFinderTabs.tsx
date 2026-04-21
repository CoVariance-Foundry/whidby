"use client";

export type TabKey = "niche" | "strategy";

interface Props {
  active: TabKey;
  onChange: (key: TabKey) => void;
}

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "niche", label: "Niche & city" },
  { key: "strategy", label: "Strategy" },
];

export default function NicheFinderTabs({ active, onChange }: Props) {
  return (
    <div
      role="tablist"
      aria-label="Search mode"
      style={{
        display: "inline-flex",
        gap: 4,
        padding: 4,
        borderRadius: 999,
        background: "var(--paper-alt)",
        border: "1px solid var(--rule)",
      }}
    >
      {TABS.map((tab) => {
        const isActive = tab.key === active;
        return (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.key)}
            style={{
              padding: "6px 14px",
              borderRadius: 999,
              fontFamily: "var(--sans)",
              fontSize: 13,
              fontWeight: isActive ? 600 : 500,
              color: isActive ? "var(--card)" : "var(--ink-2)",
              background: isActive ? "var(--accent)" : "transparent",
              border: "none",
              cursor: "pointer",
            }}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
