"use client";

import type { SignalCategory } from "@/lib/reports/signal-definitions";
import { SIGNAL_DEFINITIONS } from "@/lib/reports/signal-definitions";
import ScoreInfoHover from "@/components/reports/ScoreInfoHover";
import SignalRow from "@/components/reports/SignalRow";
import type { ScoreKey } from "@/lib/reports/score-explainers";

function scoreColor(score: number): string {
  if (score >= 75) return "#0f7a57";
  if (score >= 50) return "#a05a00";
  return "#a3292d";
}

function scoreBarBg(score: number): string {
  if (score >= 75) return "#dfede6";
  if (score >= 50) return "#f6ebd4";
  return "#f3e1e1";
}

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
        <span
          style={{
            fontFamily: "var(--serif)",
            fontVariantNumeric: "tabular-nums",
            fontWeight: 600,
            fontSize: 20,
            color: scoreColor(score),
            lineHeight: 1,
          }}
        >
          {Math.round(score)}
        </span>
        <div style={{ flex: 1, maxWidth: 80 }}>
          <div
            style={{
              height: 3,
              background: scoreBarBg(score),
              borderRadius: 2,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${Math.min(score, 100)}%`,
                background: scoreColor(score),
                borderRadius: 2,
              }}
            />
          </div>
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
