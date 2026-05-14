"use client";

import { Icon, I } from "@/lib/icons";

interface RefreshControlPanelProps {
  cadenceDays?: number;
  batchCap: number;
  selectedCount: number;
  staleCount: number;
  visibleCount: number;
  isSubmitting: boolean;
  onRefreshSelected: () => void;
  onRefreshStale: () => void;
  onRefreshVisible: () => void;
}

export default function RefreshControlPanel({
  cadenceDays = 30,
  batchCap,
  selectedCount,
  staleCount,
  visibleCount,
  isSubmitting,
  onRefreshSelected,
  onRefreshStale,
  onRefreshVisible,
}: RefreshControlPanelProps) {
  return (
    <section
      aria-label="Base reporting refresh controls"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: 16,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 14,
        flexWrap: "wrap",
      }}
    >
      <div style={{ minWidth: 220 }}>
        <div className="kicker">Base reporting refresh</div>
        <p
          style={{
            margin: "4px 0 0",
            fontFamily: "var(--sans)",
            fontSize: 13,
            color: "var(--ink-2)",
            lineHeight: 1.45,
          }}
        >
          Cached service scores refresh on a {cadenceDays}-day cadence.
          Stale and visible refreshes run up to {batchCap} targets at a time.
        </p>
      </div>

      <div
        style={{
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
          justifyContent: "flex-end",
        }}
      >
        <button
          type="button"
          className="btn-primary"
          onClick={onRefreshSelected}
          disabled={isSubmitting || selectedCount === 0}
        >
          <Icon d={I.clock} />
          Refresh selected
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={onRefreshStale}
          disabled={isSubmitting || staleCount === 0}
        >
          <Icon d={I.clock} />
          Refresh stale ({staleCount})
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={onRefreshVisible}
          disabled={isSubmitting || visibleCount === 0}
        >
          <Icon d={I.list} />
          Refresh all visible
        </button>
      </div>
    </section>
  );
}
