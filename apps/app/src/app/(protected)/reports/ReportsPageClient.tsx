"use client";

import { useMemo, useState } from "react";
import ArchetypeChipFilter from "@/components/reports/ArchetypeChipFilter";
import ReportsTable, { type TableRow } from "@/components/reports/ReportsTable";
import type { ArchetypeId } from "@/lib/archetypes";

interface Props {
  rows: TableRow[];
}

export default function ReportsPageClient({ rows }: Props) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<ArchetypeId[]>([]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (selected.length > 0 && !selected.includes(r.archetype_id))
        return false;
      if (!q) return true;
      return (
        r.niche.toLowerCase().includes(q) ||
        r.city.toLowerCase().includes(q) ||
        r.archetype_short.toLowerCase().includes(q)
      );
    });
  }, [rows, query, selected]);

  const summary = useMemo(() => {
    const byArchetype = new Map<string, number>();
    for (const r of rows) {
      byArchetype.set(
        r.archetype_short,
        (byArchetype.get(r.archetype_short) ?? 0) + 1,
      );
    }
    return {
      total: rows.length,
      top_strategy:
        [...byArchetype.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—",
    };
  }, [rows]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <section
        aria-label="Summary"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: 12,
        }}
      >
        <div
          style={{
            background: "var(--card)",
            border: "1px solid var(--rule)",
            borderRadius: 12,
            padding: "14px 18px",
          }}
        >
          <div
            style={{
              fontFamily: "var(--sans)",
              fontSize: 11.5,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--ink-3)",
              marginBottom: 4,
            }}
          >
            Total reports
          </div>
          <div
            style={{
              fontFamily: "var(--serif)",
              fontSize: 24,
              fontWeight: 600,
              color: "var(--ink)",
            }}
          >
            {summary.total}
          </div>
        </div>
        <div
          style={{
            background: "var(--card)",
            border: "1px solid var(--rule)",
            borderRadius: 12,
            padding: "14px 18px",
          }}
        >
          <div
            style={{
              fontFamily: "var(--sans)",
              fontSize: 11.5,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--ink-3)",
              marginBottom: 4,
            }}
          >
            Most common strategy
          </div>
          <div
            style={{
              fontFamily: "var(--serif)",
              fontSize: 20,
              fontWeight: 600,
              color: "var(--ink)",
            }}
          >
            {summary.top_strategy}
          </div>
        </div>
      </section>

      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Filter by niche, city, or strategy…"
        aria-label="Search reports"
        style={{
          padding: "10px 14px",
          border: "1px solid var(--rule)",
          borderRadius: 10,
          fontFamily: "var(--sans)",
          fontSize: 13.5,
          background: "var(--card)",
          color: "var(--ink)",
        }}
      />

      <ArchetypeChipFilter selected={selected} onChange={setSelected} />
      <ReportsTable rows={filtered} />

      <div
        aria-live="polite"
        style={{
          fontFamily: "var(--sans)",
          fontSize: 12.5,
          color: "var(--ink-3)",
        }}
      >
        Showing {filtered.length} of {rows.length}
      </div>
    </div>
  );
}
