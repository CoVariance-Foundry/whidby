"use client";

import type { HistoryEntry } from "@/lib/niche-finder/history-storage";

interface Props {
  pinned: HistoryEntry[];
  recent: HistoryEntry[];
  onPick: (entry: HistoryEntry) => void;
}

function Row({ entry, onPick }: { entry: HistoryEntry; onPick: (e: HistoryEntry) => void }) {
  return (
    <button
      type="button"
      onClick={() => onPick(entry)}
      aria-label={`${entry.city} ${entry.service}`}
      style={{
        width: "100%",
        textAlign: "left",
        padding: "8px 10px",
        background: "transparent",
        border: "none",
        borderRadius: 8,
        cursor: "pointer",
        fontFamily: "var(--sans)",
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
    >
      <span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ink)" }}>{entry.city}</span>
      <span style={{ fontSize: 12.5, color: "var(--ink-2)" }}>{entry.service}</span>
    </button>
  );
}

export default function PinnedRecentRail({ pinned, recent, onPick }: Props) {
  return (
    <aside style={{ display: "flex", flexDirection: "column", gap: 20, width: 260 }}>
      <section>
        <h3 style={{ fontFamily: "var(--serif)", fontSize: 14, fontWeight: 600, color: "var(--ink)", margin: "0 0 8px" }}>Pinned</h3>
        {pinned.length === 0 ? (
          <p style={{ fontFamily: "var(--sans)", fontSize: 12.5, color: "var(--ink-2)" }}>No pinned queries yet.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {pinned.map((e) => <Row key={`p-${e.at}`} entry={e} onPick={onPick} />)}
          </div>
        )}
      </section>
      <section>
        <h3 style={{ fontFamily: "var(--serif)", fontSize: 14, fontWeight: 600, color: "var(--ink)", margin: "0 0 8px" }}>Recent</h3>
        {recent.length === 0 ? (
          <p style={{ fontFamily: "var(--sans)", fontSize: 12.5, color: "var(--ink-2)" }}>No recent queries yet.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {recent.map((e) => <Row key={`r-${e.at}`} entry={e} onPick={onPick} />)}
          </div>
        )}
      </section>
    </aside>
  );
}
