"use client";

import type { SignalCategory } from "@/lib/reports/signal-definitions";
import { SIGNAL_DEFINITIONS } from "@/lib/reports/signal-definitions";
import { ScoreBar } from "@/components/ScoreVisuals";
import ScoreInfoHover from "@/components/reports/ScoreInfoHover";
import SignalRow from "@/components/reports/SignalRow";
import type { ScoreKey } from "@/lib/reports/score-explainers";

interface Props {
  title: string;
  scoreKey: ScoreKey;
  score: number;
  category: SignalCategory;
  signals: Record<string, unknown>;
}

export default function BreakdownPanel({ title, scoreKey, score, category, signals }: Props) {
  const defs = SIGNAL_DEFINITIONS[category];

  return (
    <div style={{ padding: "14px 0" }}>
      {/* Score headline */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div
          style={{
            fontFamily: "var(--serif)",
            fontStyle: "italic",
            fontSize: 12,
            color: "var(--ink-3)",
            display: "flex",
            alignItems: "center",
          }}
        >
          {title}
          <ScoreInfoHover scoreKey={scoreKey} />
        </div>
        <div style={{ flex: 1, maxWidth: 108 }}>
          <ScoreBar value={score} label={title} hideLabel />
        </div>
      </div>

      {/* Signal rows */}
      <div>
        {Object.entries(defs).map(([key, def]) => (
          <SignalRow key={key} definition={def} value={signals[key]} />
        ))}
      </div>
    </div>
  );
}
