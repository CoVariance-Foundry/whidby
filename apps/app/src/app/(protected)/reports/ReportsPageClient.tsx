"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import ArchetypeChipFilter from "@/components/reports/ArchetypeChipFilter";
import ReportsTable, { type TableRow } from "@/components/reports/ReportsTable";
import ReportDetailModal from "@/components/reports/ReportDetailModal";
import { createClient } from "@/lib/supabase/client";
import type { ArchetypeId } from "@/lib/archetypes";
import type { FullReportData } from "@/lib/niche-finder/types";
import { Icon, I } from "@/lib/icons";

type ModalState =
  | { kind: "closed" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "open"; report: FullReportData };

type SortKey = "newest" | "oldest" | "score_desc" | "score_asc";

interface Props {
  rows: TableRow[];
}

export default function ReportsPageClient({ rows: initialRows }: Props) {
  const searchParams = useSearchParams();
  const [rows, setRows] = useState(initialRows);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("newest");
  const [selected, setSelected] = useState<ArchetypeId[]>([]);
  const [modal, setModal] = useState<ModalState>({ kind: "closed" });
  const autoOpened = useRef(false);

  const openReport = useCallback(async (reportId: string) => {
    setModal({ kind: "loading" });
    try {
      const routeResponse = await fetch(`/api/agent/reports/${encodeURIComponent(reportId)}`);
      const routeJson = (await routeResponse.json().catch(() => null)) as {
        status?: string;
        message?: string;
        report?: FullReportData;
      } | null;

      if (routeResponse.ok && routeJson?.status === "success" && routeJson.report) {
        setModal({
          kind: "open",
          report: {
            ...routeJson.report,
            metros: Array.isArray(routeJson.report.metros) ? routeJson.report.metros : [],
            keyword_expansion:
              routeJson.report.keyword_expansion as FullReportData["keyword_expansion"],
            resolved_weights:
              routeJson.report.resolved_weights as Record<string, number> | null,
            meta: routeJson.report.meta as Record<string, unknown> | null,
          },
        });
        return;
      }

      setModal({
        kind: "error",
        message: routeJson?.message ?? `Failed to load report (HTTP ${routeResponse.status}).`,
      });
    } catch (err) {
      setModal({
        kind: "error",
        message: err instanceof Error ? err.message : "Failed to load report.",
      });
    }
  }, []);

  useEffect(() => {
    const openId = searchParams.get("open");
    if (openId && !autoOpened.current) {
      autoOpened.current = true;
      openReport(openId);
    }
  }, [searchParams, openReport]);

  const handleDelete = useCallback(async (reportId: string) => {
    const supabase = createClient();
    const { data: archived, error } = await supabase.rpc("archive_account_report", {
      p_report_id: reportId,
    });
    if (error) {
      throw new Error(error.message);
    }
    if (!archived) {
      throw new Error("Report not found.");
    }
    setRows((prev) => prev.filter((r) => r.id !== reportId));
    setModal({ kind: "closed" });
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matches = rows.filter((r) => {
      if (selected.length > 0 && !selected.includes(r.archetype_id))
        return false;
      if (!q) return true;
      return (
        r.niche.toLowerCase().includes(q) ||
        r.city.toLowerCase().includes(q) ||
        r.archetype_short.toLowerCase().includes(q)
      );
    });

    matches.sort((a, b) => {
      if (sort === "oldest") {
        return a.created_at.localeCompare(b.created_at);
      }
      if (sort === "score_desc") {
        return (b.opportunity_score ?? -1) - (a.opportunity_score ?? -1);
      }
      if (sort === "score_asc") {
        return (a.opportunity_score ?? 101) - (b.opportunity_score ?? 101);
      }
      return b.created_at.localeCompare(a.created_at);
    });

    return matches;
  }, [rows, query, selected, sort]);

  const summary = useMemo(() => {
    const byArchetype = new Map<string, number>();
    const scored = rows
      .map((r) => r.opportunity_score)
      .filter((score): score is number => typeof score === "number");
    for (const r of rows) {
      byArchetype.set(
        r.archetype_short,
        (byArchetype.get(r.archetype_short) ?? 0) + 1,
      );
    }
    return {
      total: rows.length,
      average_score: scored.length
        ? Math.round(scored.reduce((sum, score) => sum + score, 0) / scored.length)
        : null,
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
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 12,
        }}
      >
        {[
          { label: "Total reports", value: String(summary.total) },
          { label: "Showing", value: String(filtered.length) },
          {
            label: "Avg score",
            value: summary.average_score === null ? "—" : String(summary.average_score),
          },
          { label: "Common lens", value: summary.top_strategy },
        ].map((item) => (
          <div
            key={item.label}
            style={{
              background: "var(--card)",
              border: "1px solid var(--rule)",
              borderRadius: 8,
              padding: "14px 16px",
            }}
          >
            <div
              style={{
                fontFamily: "var(--sans)",
                fontSize: 11,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: "var(--ink-3)",
                marginBottom: 6,
              }}
            >
              {item.label}
            </div>
            <div
              style={{
                fontFamily: item.value.length > 12 ? "var(--sans)" : "var(--serif)",
                fontSize: item.value.length > 12 ? 17 : 26,
                fontWeight: 600,
                color: "var(--ink)",
                lineHeight: 1.05,
                overflowWrap: "anywhere",
              }}
            >
              {item.value}
            </div>
          </div>
        ))}
      </section>

      {rows.length === 0 ? (
        <section
          aria-label="No reports"
          style={{
            background: "var(--card)",
            border: "1px solid var(--rule)",
            borderRadius: 8,
            padding: "44px 22px",
            textAlign: "center",
          }}
        >
          <h2
            style={{
              fontFamily: "var(--serif)",
              fontSize: 22,
              color: "var(--ink)",
              margin: 0,
            }}
          >
            No reports yet
          </h2>
          <p
            style={{
              fontFamily: "var(--sans)",
              fontSize: 14,
              color: "var(--ink-2)",
              lineHeight: 1.5,
              maxWidth: 520,
              margin: "8px auto 20px",
            }}
          >
            Run your first scan from a strategy, Explore query, or niche search. Saved reports land here automatically.
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: 10, flexWrap: "wrap" }}>
            <Link href="/strategies" className="btn-primary" style={{ textDecoration: "none" }}>
              Pick a strategy <Icon d={I.arrow} />
            </Link>
            <Link href="/explore" className="btn-ghost" style={{ textDecoration: "none" }}>
              Browse Explore
            </Link>
          </div>
        </section>
      ) : (
        <>
          <section
            aria-label="Report controls"
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(220px, 1fr) minmax(180px, 220px)",
              gap: 12,
              background: "var(--card)",
              border: "1px solid var(--rule)",
              borderRadius: 8,
              padding: 12,
            }}
          >
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                minWidth: 0,
              }}
            >
              <Icon d={I.search} style={{ color: "var(--ink-3)", flexShrink: 0 }} />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Search reports"
                placeholder="Search by niche, metro, or strategy..."
                style={{
                  flex: 1,
                  minWidth: 0,
                  border: "none",
                  outline: "none",
                  fontFamily: "var(--sans)",
                  fontSize: 13.5,
                  background: "transparent",
                  color: "var(--ink)",
                }}
              />
            </label>

            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                justifyContent: "flex-end",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--sans)",
                  fontSize: 12,
                  color: "var(--ink-3)",
                  whiteSpace: "nowrap",
                }}
              >
                Sort
              </span>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortKey)}
                aria-label="Sort reports"
                style={{
                  width: "100%",
                  border: "1px solid var(--rule)",
                  borderRadius: 8,
                  padding: "8px 10px",
                  background: "var(--card)",
                  color: "var(--ink)",
                  fontFamily: "var(--sans)",
                  fontSize: 13,
                }}
              >
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="score_desc">Highest score</option>
                <option value="score_asc">Lowest score</option>
              </select>
            </label>
          </section>

          <ArchetypeChipFilter selected={selected} onChange={setSelected} />
          <ReportsTable
            rows={filtered}
            getRowHref={(id) => `/reports/${encodeURIComponent(id)}`}
          />

          <div
            aria-live="polite"
            style={{
              fontFamily: "var(--sans)",
              fontSize: 12.5,
              color: "var(--ink-3)",
            }}
          >
            Showing {filtered.length} of {rows.length} reports
          </div>
        </>
      )}

      {modal.kind === "loading" && (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 100,
            background: "rgba(31,27,22,0.35)",
            display: "grid",
            placeItems: "center",
          }}
        >
          <div
            style={{
              background: "var(--card)",
              borderRadius: 12,
              padding: "32px 40px",
              textAlign: "center",
              fontFamily: "var(--serif)",
              fontStyle: "italic",
              color: "var(--ink-2)",
              fontSize: 15,
              boxShadow: "0 20px 60px rgba(31,27,22,0.22)",
            }}
          >
            Loading report…
          </div>
        </div>
      )}

      {modal.kind === "error" && (
        <div
          onClick={() => setModal({ kind: "closed" })}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 100,
            background: "rgba(31,27,22,0.35)",
            display: "grid",
            placeItems: "center",
          }}
        >
          <div
            style={{
              background: "var(--card)",
              borderRadius: 12,
              padding: "28px 36px",
              textAlign: "center",
              maxWidth: 400,
            }}
          >
            <div
              style={{
                fontFamily: "var(--serif)",
                fontSize: 15,
                color: "var(--danger)",
                marginBottom: 14,
              }}
            >
              {modal.message}
            </div>
            <button
              className="btn-ghost"
              onClick={() => setModal({ kind: "closed" })}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {modal.kind === "open" && (
        <ReportDetailModal
          report={modal.report}
          onClose={() => setModal({ kind: "closed" })}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}
