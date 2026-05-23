"use client";

import Link from "next/link";
import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";
import { scoreToneForValue, type ScoreToneKey } from "@/lib/design-tokens";
import ScoreInfoHover from "@/components/reports/ScoreInfoHover";
import { Icon, I } from "@/lib/icons";

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

function scoreLabelForTone(tone: ScoreToneKey): string {
  switch (tone) {
    case "high":
      return "High";
    case "good":
      return "Good";
    case "warning":
      return "Warning";
    case "danger":
      return "Danger";
    case "muted":
      return "Unknown";
  }
}

interface Props {
  rows: TableRow[];
  onRowClick?: (id: string) => void;
  getRowHref?: (id: string) => string;
}

export default function ReportsTable({ rows, onRowClick, getRowHref }: Props) {
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
          borderRadius: 8,
        }}
      >
        No reports match your search.
      </div>
    );
  }

  return (
    <div
      role="list"
      aria-label="Reports"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      {rows.map((r) => {
        const href = getRowHref?.(r.id);
        const openLabel = `Open report for ${r.niche} in ${r.city}`;
        const isInteractive = Boolean(href || onRowClick);
        const scoreTone = scoreToneForValue(r.opportunity_score);
        const titleBlock = (
          <>
            <div
              style={{
                display: "flex",
                gap: 8,
                flexWrap: "wrap",
                alignItems: "center",
                marginBottom: 5,
              }}
            >
              <h2
                title={`${r.niche} · ${r.city}`}
                style={{
                  margin: 0,
                  fontFamily: "var(--serif)",
                  fontSize: 18,
                  fontWeight: 600,
                  lineHeight: 1.2,
                  minWidth: 0,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {r.niche}
              </h2>
              <span
                className={archetypeGlyphClass(r.archetype_id)}
                style={{
                  display: "inline-block",
                  padding: "2px 9px",
                  borderRadius: 999,
                  fontSize: 10.5,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                }}
              >
                {r.archetype_short}
              </span>
            </div>
            <div
              style={{
                display: "flex",
                gap: 10,
                flexWrap: "wrap",
                alignItems: "center",
                fontFamily: "var(--sans)",
                fontSize: 12.5,
                color: "var(--ink-2)",
              }}
            >
              <span>{r.city}</span>
              <span aria-hidden="true" style={{ color: "var(--ink-3)" }}>
                ·
              </span>
              <span>{formatDate(r.created_at)}</span>
              <span aria-hidden="true" style={{ color: "var(--ink-3)" }}>
                ·
              </span>
              <span>Spec v{r.spec_version}</span>
            </div>
          </>
        );
        const scoreBlock = (
          <>
            <div
              style={{
                fontFamily: "var(--mono)",
                fontSize: 24,
                fontWeight: 800,
                lineHeight: 1,
                color: scoreTone.text,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {r.opportunity_score ?? "—"}
            </div>
            <div
              style={{
                fontFamily: "var(--sans)",
                fontSize: 11,
                color: "var(--ink-3)",
                marginTop: 4,
              }}
            >
              {scoreLabelForTone(scoreTone.key)}
            </div>
          </>
        );

        return (
          <div key={r.id} role="listitem">
            <article
              style={{
                position: "relative",
                display: "grid",
                gridTemplateColumns: "minmax(0, 1fr) auto",
                gap: 18,
                alignItems: "center",
                background: "var(--card)",
                border: "1px solid var(--rule)",
                borderRadius: 8,
                padding: "16px 18px",
                color: "var(--ink)",
                cursor: isInteractive ? "pointer" : "default",
              }}
            >
              {href ? (
                <Link
                  href={href}
                  aria-label={openLabel}
                  style={{
                    position: "absolute",
                    inset: 0,
                    zIndex: 1,
                    borderRadius: 8,
                    color: "inherit",
                    textDecoration: "none",
                  }}
                />
              ) : onRowClick ? (
                <button
                  type="button"
                  onClick={() => onRowClick(r.id)}
                  aria-label={openLabel}
                  style={{
                    position: "absolute",
                    inset: 0,
                    zIndex: 1,
                    border: "none",
                    borderRadius: 8,
                    padding: 0,
                    background: "transparent",
                    cursor: "pointer",
                  }}
                />
              ) : null}
              <div style={{ minWidth: 0, position: "relative", zIndex: 0 }}>
                {titleBlock}
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  position: "relative",
                  zIndex: 2,
                  pointerEvents: "none",
                }}
              >
                <div style={{ textAlign: "right" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "flex-end",
                      fontFamily: "var(--serif)",
                      fontStyle: "italic",
                      fontSize: 11,
                      color: "var(--ink-3)",
                      marginBottom: 4,
                    }}
                  >
                    Top score
                    <span style={{ pointerEvents: "auto", cursor: "default" }}>
                      <ScoreInfoHover scoreKey="opportunity" />
                    </span>
                  </div>
                  {scoreBlock}
                </div>
                <span aria-hidden="true" style={{ display: "inline-flex" }}>
                  <Icon d={I.arrow} style={{ color: "var(--ink-3)" }} />
                </span>
              </div>
            </article>
          </div>
        );
      })}
    </div>
  );
}
