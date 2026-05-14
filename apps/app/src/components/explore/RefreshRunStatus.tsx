"use client";

import Link from "next/link";
import type { ExploreRefreshRunResponse } from "@/lib/explore-refresh/types";

interface RefreshRunStatusProps {
  run: ExploreRefreshRunResponse | null;
  error: string | null;
}

export default function RefreshRunStatus({ run, error }: RefreshRunStatusProps) {
  if (error) {
    return (
      <div
        role="alert"
        style={{
          border: "1px solid color-mix(in srgb, #b42318 35%, var(--rule))",
          borderRadius: 8,
          background: "color-mix(in srgb, #b42318 8%, var(--card))",
          color: "#8a1f14",
          padding: "10px 12px",
          fontFamily: "var(--sans)",
          fontSize: 13,
        }}
      >
        {error}
      </div>
    );
  }

  if (!run) return null;

  return (
    <div
      role="status"
      style={{
        border: "1px solid var(--rule)",
        borderRadius: 8,
        background: "var(--paper)",
        color: "var(--ink-2)",
        padding: "10px 12px",
        fontFamily: "var(--sans)",
        fontSize: 13,
        display: "flex",
        gap: 8,
        alignItems: "center",
        flexWrap: "wrap",
      }}
    >
      <span style={{ minWidth: 0, overflowWrap: "anywhere" }}>
        Refresh run {run.run_id} {run.status.replace(/_/g, " ")}.
      </span>
      {run.run_id && (
        <Link
          href={`/explore?refresh_run=${encodeURIComponent(run.run_id)}`}
          aria-label={`View refresh run ${run.run_id}`}
          style={{ color: "var(--accent-ink)", fontWeight: 650 }}
        >
          View run
        </Link>
      )}
    </div>
  );
}
