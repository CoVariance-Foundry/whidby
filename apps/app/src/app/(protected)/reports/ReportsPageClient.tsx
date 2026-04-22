"use client";

import { useCallback, useMemo, useState } from "react";
import ArchetypeChipFilter from "@/components/reports/ArchetypeChipFilter";
import ReportsTable, { type TableRow } from "@/components/reports/ReportsTable";
import ReportDetailModal from "@/components/reports/ReportDetailModal";
import { createClient } from "@/lib/supabase/client";
import type { ArchetypeId } from "@/lib/archetypes";
import type { FullReportData } from "@/lib/niche-finder/types";

type ModalState =
  | { kind: "closed" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "open"; report: FullReportData };

interface Props {
  rows: TableRow[];
}

export default function ReportsPageClient({ rows: initialRows }: Props) {
  const [rows, setRows] = useState(initialRows);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<ArchetypeId[]>([]);
  const [modal, setModal] = useState<ModalState>({ kind: "closed" });

  const handleRowClick = useCallback(async (reportId: string) => {
    setModal({ kind: "loading" });
    try {
      const supabase = createClient();
      const { data, error } = await supabase
        .from("reports")
        .select(
          "id, created_at, spec_version, niche_keyword, geo_scope, geo_target, report_depth, strategy_profile, resolved_weights, keyword_expansion, metros, meta",
        )
        .eq("id", reportId)
        .single();

      if (error || !data) {
        setModal({ kind: "error", message: error?.message ?? "Report not found." });
        return;
      }

      setModal({
        kind: "open",
        report: {
          ...data,
          metros: Array.isArray(data.metros) ? data.metros : [],
          keyword_expansion: data.keyword_expansion as FullReportData["keyword_expansion"],
          resolved_weights: data.resolved_weights as Record<string, number> | null,
          meta: data.meta as Record<string, unknown> | null,
        },
      });
    } catch (err) {
      setModal({
        kind: "error",
        message: err instanceof Error ? err.message : "Failed to load report.",
      });
    }
  }, []);

  const handleDelete = useCallback(async (reportId: string) => {
    const supabase = createClient();
    const { error } = await supabase.from("reports").delete().eq("id", reportId);
    if (error) throw new Error(error.message);
    setRows((prev) => prev.filter((r) => r.id !== reportId));
    setModal({ kind: "closed" });
  }, []);

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
      <ReportsTable rows={filtered} onRowClick={handleRowClick} />

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
