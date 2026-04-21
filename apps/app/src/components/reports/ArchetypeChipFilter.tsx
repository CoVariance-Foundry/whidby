"use client";

import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";

interface Props {
  selected: ArchetypeId[];
  onChange: (next: ArchetypeId[]) => void;
}

export default function ArchetypeChipFilter({ selected, onChange }: Props) {
  const allSelected = selected.length === 0;

  function toggle(id: ArchetypeId) {
    if (selected.includes(id)) {
      onChange(selected.filter((s) => s !== id));
    } else {
      onChange([...selected, id]);
    }
  }

  return (
    <div
      role="group"
      aria-label="Filter by archetype"
      style={{
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
        alignItems: "center",
      }}
    >
      <button
        type="button"
        onClick={() => onChange([])}
        style={{
          padding: "6px 14px",
          borderRadius: 999,
          fontFamily: "var(--sans)",
          fontSize: 12.5,
          fontWeight: allSelected ? 600 : 500,
          color: allSelected ? "var(--card)" : "var(--ink-2)",
          background: allSelected ? "var(--accent)" : "transparent",
          border: `1px solid ${allSelected ? "var(--accent)" : "var(--rule)"}`,
          cursor: "pointer",
        }}
      >
        All strategies
      </button>

      {ARCHETYPES.map((a) => {
        const isOn = selected.includes(a.id);
        return (
          <button
            key={a.id}
            type="button"
            onClick={() => toggle(a.id)}
            className={isOn ? a.glyph : undefined}
            aria-pressed={isOn}
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              fontFamily: "var(--sans)",
              fontSize: 12.5,
              fontWeight: 600,
              border: `1px solid ${isOn ? "transparent" : "var(--rule)"}`,
              background: isOn ? undefined : "transparent",
              color: isOn ? undefined : "var(--ink-2)",
              cursor: "pointer",
            }}
          >
            {a.short}
          </button>
        );
      })}
    </div>
  );
}
