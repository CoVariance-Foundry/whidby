"use client";

import Link from "next/link";
import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { Icon, I } from "@/lib/icons";
import type { ReportListRow } from "@/lib/niche-finder/reports-mapper";

// Opportunity score thresholds → label + color token
function ScorePill({ score }: { score: number | null }) {
  if (score === null) {
    return (
      <span
        style={{
          display: "inline-block",
          padding: "2px 8px",
          borderRadius: 4,
          fontSize: 11.5,
          fontFamily: "var(--mono)",
          background: "var(--paper-alt)",
          color: "var(--ink-3)",
          border: "1px solid var(--rule)",
        }}
      >
        Unknown
      </span>
    );
  }
  const label = score >= 75 ? "High" : score >= 50 ? "Medium" : "Low";
  const color =
    score >= 75
      ? { bg: "#e6f4ea", border: "#a8d5b5", text: "#1a6630" }
      : score >= 50
      ? { bg: "#fff8e1", border: "#ffe082", text: "#795500" }
      : { bg: "#fce8e6", border: "#f5bcb6", text: "#a32b22" };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 11.5,
        fontFamily: "var(--mono)",
        background: color.bg,
        color: color.text,
        border: `1px solid ${color.border}`,
      }}
    >
      <span
        style={{
          fontWeight: 700,
          fontSize: 13,
          fontVariantNumeric: "tabular-nums",
          lineHeight: 1,
        }}
      >
        {score}
      </span>
      {label}
    </span>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

interface ReportsViewProps {
  rows: ReportListRow[];
}

const TABLE_GRID = "minmax(0,2.6fr) 1.4fr 120px 100px";

export default function ReportsView({ rows }: ReportsViewProps) {
  const [query, setQuery] = useState("");

  const trimmedQuery = query.trim().toLowerCase();

  const filtered = rows.filter((r) => {
    if (!trimmedQuery) return true;
    return (
      r.niche_keyword.toLowerCase().includes(trimmedQuery) ||
      r.geo_target.toLowerCase().includes(trimmedQuery) ||
      r.id.toLowerCase().includes(trimmedQuery)
    );
  });

  const total = rows.length;

  return (
    <div className="app density-roomy">
      <Sidebar active="reports" />
      <div className="main">
        <Topbar crumbs={["Reports"]} />
        <div className="page">
          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "space-between",
              gap: 24,
              marginBottom: 22,
            }}
          >
            <div>
              <div className="kicker">Archive</div>
              <div className="page-h1" style={{ marginTop: 6 }}>
                Reports
              </div>
              <div className="page-sub">
                Every search you&apos;ve run and saved. Open a report to re&#8209;view the
                ranked metros, signals, and guidance at the time it was scored.
              </div>
            </div>
            <Link
              href="/niche-finder"
              className="btn-primary"
              style={{ textDecoration: "none" }}
            >
              <Icon d={I.plus} /> New report
            </Link>
          </div>

          {/* Summary stats */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, 1fr)",
              gap: 12,
              marginBottom: 22,
            }}
          >
            {[
              { label: "Total reports", value: String(total) },
              { label: "Showing", value: String(filtered.length) },
            ].map((s) => (
              <div
                key={s.label}
                style={{
                  background: "var(--card)",
                  border: "1px solid var(--rule)",
                  borderRadius: 10,
                  padding: "14px 16px",
                }}
              >
                <div className="field-label" style={{ marginBottom: 6 }}>
                  {s.label}
                </div>
                <div
                  style={{
                    fontFamily: "var(--serif)",
                    fontSize: 26,
                    fontWeight: 600,
                    letterSpacing: "-0.4px",
                    lineHeight: 1,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {s.value}
                </div>
              </div>
            ))}
          </div>

          {/* Toolbar */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 14,
              background: "var(--card)",
              border: "1px solid var(--rule)",
              borderRadius: 10,
              padding: "12px 14px",
            }}
          >
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Icon d={I.search} />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by niche, metro, or ID…"
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  fontSize: 13,
                  color: "var(--ink)",
                  fontFamily: "inherit",
                }}
              />
            </div>
            <button className="btn-ghost">
              <Icon d={I.save} /> Export
            </button>
          </div>

          {/* Table */}
          <div className="results">
            <div
              className="res-row head"
              style={{ gridTemplateColumns: TABLE_GRID }}
            >
              <div>Niche</div>
              <div>Market</div>
              <div>Score</div>
              <div>Date</div>
            </div>

            {/* Empty state — no data at all */}
            {total === 0 && (
              <div
                style={{
                  padding: "48px 18px",
                  textAlign: "center",
                  color: "var(--ink-3)",
                  fontFamily: "var(--serif)",
                  fontStyle: "italic",
                  fontSize: 14,
                }}
              >
                No reports yet — run a niche finder to generate your first report.{" "}
                <Link
                  href="/niche-finder"
                  style={{ color: "var(--accent)", textDecoration: "underline" }}
                >
                  Go to Niche Finder
                </Link>
              </div>
            )}

            {/* Search returned nothing but there are rows */}
            {total > 0 && filtered.length === 0 && (
              <div
                style={{
                  padding: "40px 18px",
                  textAlign: "center",
                  color: "var(--ink-3)",
                  fontFamily: "var(--serif)",
                  fontStyle: "italic",
                  fontSize: 13,
                }}
              >
                No reports match your search.
              </div>
            )}

            {filtered.map((r) => (
              <Link
                key={r.id}
                href={`/reports/${r.id}`}
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <div
                  className="res-row"
                  style={{
                    gridTemplateColumns: TABLE_GRID,
                    alignItems: "center",
                    paddingTop: 14,
                    paddingBottom: 14,
                    cursor: "pointer",
                  }}
                >
                  {/* Niche keyword */}
                  <div style={{ minWidth: 0 }}>
                    <div
                      className="res-metro"
                      title={r.niche_keyword}
                      style={{
                        lineHeight: 1.3,
                        minWidth: 0,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {r.niche_keyword}
                    </div>
                    <div
                      className="res-metro-sub"
                      style={{ marginTop: 3, fontFamily: "var(--mono)", fontSize: 10.5 }}
                    >
                      {r.id.slice(0, 8)}
                    </div>
                  </div>

                  {/* Geo target */}
                  <div
                    style={{
                      fontSize: 12.5,
                      color: "var(--ink-2)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {r.geo_target}
                  </div>

                  {/* Opportunity score pill */}
                  <div>
                    <ScorePill score={r.opportunity_score} />
                  </div>

                  {/* Date */}
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--ink-3)",
                      fontFamily: "var(--serif)",
                      fontStyle: "italic",
                    }}
                  >
                    {formatDate(r.created_at)}
                  </div>
                </div>
              </Link>
            ))}
          </div>

          <div
            style={{
              marginTop: 14,
              fontSize: 12,
              color: "var(--ink-3)",
              fontFamily: "var(--serif)",
              fontStyle: "italic",
            }}
          >
            Showing {filtered.length} of {total} reports
          </div>
        </div>
      </div>
    </div>
  );
}
