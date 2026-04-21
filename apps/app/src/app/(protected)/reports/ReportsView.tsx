"use client";

import Link from "next/link";
import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import StatusPill, { type ReportStatus } from "@/components/StatusPill";
import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";
import { Icon, I } from "@/lib/icons";

type ReportKind = "strategy" | "niche";

interface ReportRow {
  id: string;
  title: string;
  kind: ReportKind;
  archetypeId: ArchetypeId;
  metros: number;
  top: number;
  avg: number;
  status: ReportStatus;
  owner: string;
  date: string;
}

const REPORT_ROWS: ReportRow[] = [
  { id: "R‑0148", title: "Mountain West roofing sweep",           kind: "strategy", archetypeId: "PACK_VULN", metros: 5,  top: 82, avg: 72.4, status: "complete", owner: "AR", date: "Jan 18" },
  { id: "R‑0147", title: "roofing · Phoenix, AZ",                 kind: "niche",    archetypeId: "AGG",       metros: 1,  top: 42, avg: 42.0, status: "complete", owner: "AR", date: "Jan 18" },
  { id: "R‑0146", title: "Florida inland flood niches",           kind: "strategy", archetypeId: "FRAG_WEAK", metros: 8,  top: 77, avg: 64.1, status: "complete", owner: "AR", date: "Jan 17" },
  { id: "R‑0145", title: "water damage · Tampa, FL",              kind: "niche",    archetypeId: "PACK_EST",  metros: 1,  top: 61, avg: 61.0, status: "complete", owner: "AR", date: "Jan 16" },
  { id: "R‑0144", title: "Fast‑path pack opportunities",          kind: "strategy", archetypeId: "PACK_VULN", metros: 12, top: 84, avg: 70.9, status: "running",  owner: "AR", date: "Jan 16" },
  { id: "R‑0143", title: "garage door repair · Austin, TX",       kind: "niche",    archetypeId: "FRAG_COMP", metros: 1,  top: 54, avg: 54.0, status: "complete", owner: "AR", date: "Jan 14" },
  { id: "R‑0142", title: "Mid‑tier aggregator plays",             kind: "strategy", archetypeId: "AGG",       metros: 6,  top: 68, avg: 59.3, status: "complete", owner: "AR", date: "Jan 12" },
  { id: "R‑0141", title: "tree service · Southeast sweep",        kind: "strategy", archetypeId: "FRAG_WEAK", metros: 7,  top: 76, avg: 62.8, status: "complete", owner: "JP", date: "Jan 11" },
  { id: "R‑0140", title: "barren niche probe — secondary cities", kind: "strategy", archetypeId: "BARREN",    metros: 9,  top: 71, avg: 58.2, status: "archived", owner: "AR", date: "Jan 08" },
  { id: "R‑0139", title: "gutter installation · Boise, ID",       kind: "niche",    archetypeId: "PACK_VULN", metros: 1,  top: 79, avg: 79.0, status: "complete", owner: "AR", date: "Jan 07" },
];

const TABLE_GRID = "82px minmax(0,2.6fr) 1.2fr 80px 80px 90px 110px 60px";

type KindFilter = "all" | ReportKind;

export default function ReportsView() {
  const [selectedArchs, setSelectedArchs] = useState<ArchetypeId[]>([]);
  const [kindFilter, setKindFilter] = useState<KindFilter>("all");
  const [query, setQuery] = useState("");

  const trimmedQuery = query.trim().toLowerCase();

  const rows = REPORT_ROWS.filter((r) => {
    if (kindFilter !== "all" && r.kind !== kindFilter) return false;
    if (selectedArchs.length > 0 && !selectedArchs.includes(r.archetypeId)) return false;
    if (trimmedQuery && !r.title.toLowerCase().includes(trimmedQuery) && !r.id.toLowerCase().includes(trimmedQuery)) {
      return false;
    }
    return true;
  });

  const toggleArch = (id: ArchetypeId) =>
    setSelectedArchs((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  const total = REPORT_ROWS.length;
  const running = REPORT_ROWS.filter((r) => r.status === "running").length;
  const metros = REPORT_ROWS.reduce((a, b) => a + b.metros, 0);
  const avgTop = (REPORT_ROWS.reduce((a, b) => a + b.top, 0) / total).toFixed(1);

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
                Every search you&apos;ve run and saved. Open a report to re‑view the
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
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 12,
              marginBottom: 22,
            }}
          >
            {[
              { label: "Total reports", value: String(total) },
              { label: "Currently running", value: String(running) },
              { label: "Metros scored", value: String(metros) },
              { label: "Avg top score", value: avgTop },
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
              flexDirection: "column",
              gap: 12,
              marginBottom: 14,
              background: "var(--card)",
              border: "1px solid var(--rule)",
              borderRadius: 10,
              padding: "12px 14px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
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
                  placeholder="Search reports by title, niche, metro…"
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
              <div
                style={{
                  display: "flex",
                  gap: 4,
                  padding: 3,
                  background: "var(--paper-alt)",
                  border: "1px solid var(--rule)",
                  borderRadius: 8,
                }}
              >
                {(
                  [
                    { v: "all", label: "All" },
                    { v: "strategy", label: "Strategy" },
                    { v: "niche", label: "Niche & city" },
                  ] as const
                ).map((o) => {
                  const on = kindFilter === o.v;
                  return (
                    <button
                      key={o.v}
                      onClick={() => setKindFilter(o.v)}
                      style={{
                        padding: "5px 10px",
                        fontSize: 11.5,
                        borderRadius: 5,
                        fontFamily: "var(--serif)",
                        fontStyle: on ? "normal" : "italic",
                        fontWeight: on ? 600 : 400,
                        background: on ? "var(--card)" : "transparent",
                        boxShadow: on ? "0 0 0 1px var(--rule)" : "none",
                        color: on ? "var(--ink)" : "var(--ink-2)",
                      }}
                    >
                      {o.label}
                    </button>
                  );
                })}
              </div>
              <button className="btn-ghost">
                <Icon d={I.save} /> Export
              </button>
            </div>

            {/* Archetype chip filter */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                paddingTop: 10,
                borderTop: "1px dashed var(--rule)",
              }}
            >
              <div
                className="field-label"
                style={{ margin: 0, flexShrink: 0 }}
              >
                Strategy
              </div>
              <div className="chip-row" style={{ flex: 1 }}>
                <button
                  className="chip"
                  onClick={() => setSelectedArchs([])}
                  style={
                    selectedArchs.length === 0
                      ? {
                          background: "var(--accent-soft)",
                          borderColor: "var(--accent)",
                          color: "var(--accent-ink)",
                        }
                      : {}
                  }
                >
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: 3,
                      background:
                        selectedArchs.length === 0
                          ? "var(--accent)"
                          : "var(--ink-3)",
                    }}
                  />
                  All strategies
                </button>
                {ARCHETYPES.map((a) => {
                  const on = selectedArchs.includes(a.id);
                  return (
                    <button
                      key={a.id}
                      className="chip"
                      onClick={() => toggleArch(a.id)}
                      style={
                        on
                          ? {
                              background: "var(--accent-soft)",
                              borderColor: "var(--accent)",
                              color: "var(--accent-ink)",
                            }
                          : {}
                      }
                    >
                      <span
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: 3,
                          background: on ? "var(--accent)" : "var(--ink-3)",
                        }}
                      />
                      {a.short}
                    </button>
                  );
                })}
              </div>
              {selectedArchs.length > 0 && (
                <button
                  onClick={() => setSelectedArchs([])}
                  style={{
                    fontSize: 11,
                    color: "var(--ink-3)",
                    fontFamily: "var(--serif)",
                    fontStyle: "italic",
                    flexShrink: 0,
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Table */}
          <div className="results">
            <div
              className="res-row head"
              style={{ gridTemplateColumns: TABLE_GRID }}
            >
              <div>ID</div>
              <div>Report</div>
              <div>Strategy</div>
              <div>Metros</div>
              <div>Top</div>
              <div>Status</div>
              <div>Updated</div>
              <div></div>
            </div>

            {rows.length === 0 && (
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
                No reports match the selected filters.
              </div>
            )}

            {rows.map((r) => {
              const arch = ARCHETYPES.find((a) => a.id === r.archetypeId);
              return (
                <div
                  key={r.id}
                  className="res-row"
                  style={{
                    gridTemplateColumns: TABLE_GRID,
                    alignItems: "center",
                    paddingTop: 14,
                    paddingBottom: 14,
                  }}
                >
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 11.5,
                      color: "var(--ink-3)",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {r.id}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        minWidth: 0,
                      }}
                    >
                      <Icon
                        d={r.kind === "strategy" ? I.sparkle : I.search}
                        size={12}
                      />
                      <div
                        className="res-metro"
                        title={r.title}
                        style={{
                          lineHeight: 1.3,
                          minWidth: 0,
                          flex: 1,
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {r.title}
                      </div>
                    </div>
                    <div
                      className="res-metro-sub"
                      style={{ marginLeft: 20, marginTop: 4 }}
                    >
                      by {r.owner} ·{" "}
                      {r.metros === 1 ? "single metro" : r.metros + " metros"}
                    </div>
                  </div>
                  <div
                    title={arch?.title ?? ""}
                    style={{
                      fontSize: 12.5,
                      color: "var(--ink-2)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {arch ? arch.short : "—"}
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--serif)",
                      fontSize: 15,
                      fontWeight: 600,
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {r.metros}
                  </div>
                  <div>
                    <div className="score" style={{ fontSize: 17 }}>
                      {r.top}
                    </div>
                    <div style={{ width: 48, marginTop: 4 }}>
                      <div className="score-bar">
                        <div style={{ width: r.top + "%" }} />
                      </div>
                    </div>
                  </div>
                  <div>
                    <StatusPill status={r.status} />
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--ink-3)",
                      fontFamily: "var(--serif)",
                      fontStyle: "italic",
                    }}
                  >
                    {r.date}
                  </div>
                  <div>
                    <button className="res-open" aria-label={"Open " + r.id}>
                      <Icon d={I.arrow} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div
            style={{
              marginTop: 14,
              fontSize: 12,
              color: "var(--ink-3)",
              fontFamily: "var(--serif)",
              fontStyle: "italic",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>
              Showing {rows.length} of {total} reports
            </span>
            <div style={{ display: "flex", gap: 6 }}>
              <button className="btn-ghost" style={{ padding: "6px 10px" }}>
                Previous
              </button>
              <button className="btn-ghost" style={{ padding: "6px 10px" }}>
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
