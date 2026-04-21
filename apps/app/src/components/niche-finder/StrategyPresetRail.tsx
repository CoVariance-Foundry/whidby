"use client";

import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";

interface Props {
  onPick: (id: ArchetypeId) => void;
}

export default function StrategyPresetRail({ onPick }: Props) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
        gap: 12,
      }}
    >
      {ARCHETYPES.map((a) => (
        <button
          key={a.id}
          type="button"
          onClick={() => onPick(a.id)}
          aria-label={a.short}
          style={{
            textAlign: "left",
            background: "var(--card)",
            border: "1px solid var(--rule)",
            borderRadius: 10,
            padding: "14px 16px",
            display: "flex",
            flexDirection: "column",
            gap: 6,
            cursor: "pointer",
            fontFamily: "var(--sans)",
          }}
        >
          <span
            className={a.glyph}
            style={{
              display: "inline-block",
              fontSize: 11,
              padding: "2px 8px",
              borderRadius: 999,
              alignSelf: "flex-start",
              fontWeight: 600,
              letterSpacing: "0.02em",
              textTransform: "uppercase",
            }}
          >
            {a.short}
          </span>
          <span style={{ fontSize: 13, color: "var(--ink)", fontWeight: 500 }}>{a.hint}</span>
          <span style={{ fontSize: 12, color: "var(--ink-2)" }}>{a.strat}</span>
        </button>
      ))}
    </div>
  );
}
