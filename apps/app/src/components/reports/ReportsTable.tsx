"use client";

import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";
import ScoreInfoHover from "@/components/reports/ScoreInfoHover";

export interface TableRow {
  id: string;
  niche: string;
  city: string;
  archetype_id: ArchetypeId;
  archetype_short: string;
  opportunity_score: number | null;
  spec_version: string;
  created_at: string;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function archetypeGlyphClass(id: ArchetypeId): string {
  return ARCHETYPES.find((a) => a.id === id)?.glyph ?? "arch-mixed";
}

interface Props {
  rows: TableRow[];
  onRowClick?: (id: string) => void;
}

export default function ReportsTable({ rows, onRowClick }: Props) {
  if (rows.length === 0) {
    return (
      <div
        role="status"
        style={{
          padding: "24px 20px",
          textAlign: "center",
          fontFamily: "var(--sans)",
          fontSize: 14,
          color: "var(--ink-2)",
          background: "var(--card)",
          border: "1px solid var(--rule)",
          borderRadius: 12,
        }}
      >
        No reports match the current filters.
      </div>
    );
  }

  return (
    <div
      role="table"
      aria-label="Reports"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        overflow: "hidden",
      }}
    >
      <div
        role="row"
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0,3fr) 1fr 1fr 1fr",
          padding: "10px 16px",
          background: "var(--paper-alt)",
          borderBottom: "1px solid var(--rule)",
          fontFamily: "var(--sans)",
          fontSize: 11.5,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: "var(--ink-3)",
          gap: 12,
        }}
      >
        <span role="columnheader">Report</span>
        <span role="columnheader">Strategy</span>
        <span role="columnheader" style={{ textAlign: "right", display: "flex", alignItems: "center", justifyContent: "flex-end" }}>
          Top score
          <ScoreInfoHover scoreKey="opportunity" />
        </span>
        <span role="columnheader" style={{ textAlign: "right" }}>
          Date
        </span>
      </div>

      {rows.map((r) => (
        <div
          key={r.id}
          role="row"
          className={onRowClick ? "report-row-clickable" : undefined}
          tabIndex={onRowClick ? 0 : undefined}
          onClick={onRowClick ? () => onRowClick(r.id) : undefined}
          onKeyDown={
            onRowClick
              ? (e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onRowClick(r.id);
                  }
                }
              : undefined
          }
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,3fr) 1fr 1fr 1fr",
            padding: "12px 16px",
            borderBottom: "1px solid var(--rule)",
            fontFamily: "var(--sans)",
            fontSize: 13.5,
            color: "var(--ink)",
            alignItems: "flex-start",
            gap: 12,
            cursor: onRowClick ? "pointer" : undefined,
            transition: "background 0.1s",
          }}
        >
          <span
            role="cell"
            style={{
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={`${r.niche} · ${r.city}`}
          >
            {r.niche} · {r.city}
          </span>
          <span role="cell">
            <span
              className={archetypeGlyphClass(r.archetype_id)}
              style={{
                display: "inline-block",
                padding: "2px 10px",
                borderRadius: 999,
                fontSize: 11.5,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.02em",
              }}
            >
              {r.archetype_short}
            </span>
          </span>
          <span
            role="cell"
            style={{
              textAlign: "right",
              fontFamily: "var(--mono)",
              color: "var(--accent-ink)",
              fontWeight: 600,
            }}
          >
            {r.opportunity_score ?? "—"}
          </span>
          <span
            role="cell"
            style={{
              textAlign: "right",
              fontFamily: "var(--mono)",
              fontSize: 12,
              color: "var(--ink-3)",
            }}
          >
            {formatDate(r.created_at)}
          </span>
        </div>
      ))}
    </div>
  );
}
