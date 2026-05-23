"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Icon, I } from "@/lib/icons";
import { createClient } from "@/lib/supabase/client";
import type { FullReportData } from "@/lib/niche-finder/types";

interface ReportActionsProps {
  report: FullReportData;
  onDelete?: (reportId: string) => Promise<void>;
  enableArchiveDelete?: boolean;
}

function buttonStyle(variant: "ghost" | "danger" = "ghost"): React.CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    minHeight: 34,
    padding: "7px 11px",
    borderRadius: 8,
    border: variant === "danger" ? "1px solid var(--danger)" : "1px solid var(--rule-strong)",
    background: variant === "danger" ? "var(--danger)" : "var(--card)",
    color: variant === "danger" ? "#fff" : "var(--ink-2)",
    fontFamily: "var(--sans)",
    fontSize: 12,
    fontWeight: 700,
    cursor: "pointer",
    textDecoration: "none",
  };
}

function filenameForReport(report: FullReportData): string {
  const label = [report.niche_keyword, report.geo_target, report.created_at.slice(0, 10)]
    .filter(Boolean)
    .join("-");
  const safe = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `widby-report-${safe || report.id}.json`;
}

function exportReport(report: FullReportData) {
  const blob = new Blob([JSON.stringify(report, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filenameForReport(report);
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function ReportActions({
  report,
  onDelete,
  enableArchiveDelete = false,
}: ReportActionsProps) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canDelete = Boolean(onDelete || enableArchiveDelete);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      if (onDelete) {
        await onDelete(report.id);
        setDeleting(false);
        setConfirming(false);
      } else {
        const supabase = createClient();
        const { data: archived, error: archiveError } = await supabase.rpc("archive_account_report", {
          p_report_id: report.id,
        });
        if (archiveError) throw new Error(archiveError.message);
        if (!archived) throw new Error("Report not found.");
        router.push("/reports");
        router.refresh();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete report.");
      setDeleting(false);
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
      <button type="button" onClick={() => exportReport(report)} style={buttonStyle("ghost")}>
        <Icon d={I.save} size={13} />
        Export JSON
      </button>

      {canDelete && !confirming ? (
        <button
          type="button"
          onClick={() => setConfirming(true)}
          disabled={deleting}
          style={{ ...buttonStyle("ghost"), color: "var(--danger)" }}
        >
          <Icon d={I.x} size={13} />
          Delete report
        </button>
      ) : null}

      {canDelete && confirming ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: "var(--danger-soft)",
            border: "1px solid var(--danger)",
            borderRadius: 8,
            padding: 6,
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontFamily: "var(--serif)",
              fontStyle: "italic",
              fontSize: 12,
              color: "var(--danger)",
            }}
          >
            This can&apos;t be undone
          </span>
          <button
            type="button"
            disabled={deleting}
            onClick={handleDelete}
            style={{
              ...buttonStyle("danger"),
              minHeight: 28,
              padding: "4px 10px",
              cursor: deleting ? "wait" : "pointer",
              opacity: deleting ? 0.6 : 1,
            }}
          >
            {deleting ? "Deleting..." : "Delete"}
          </button>
          <button
            type="button"
            disabled={deleting}
            onClick={() => {
              setConfirming(false);
              setError(null);
            }}
            style={{
              ...buttonStyle("ghost"),
              minHeight: 28,
              padding: "4px 10px",
            }}
          >
            Cancel
          </button>
        </div>
      ) : null}

      {error ? (
        <span style={{ color: "var(--danger)", fontSize: 12, fontFamily: "var(--sans)" }}>
          {error}
        </span>
      ) : null}
    </div>
  );
}
