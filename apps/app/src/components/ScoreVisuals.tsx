import { scoreToneForValue, type ScoreTone } from "@/lib/design-tokens";

type ScoreValue = number | null | undefined;

export interface ScoreCircleProps {
  value: ScoreValue;
  size?: number;
  label?: string;
  max?: number;
}

export interface ScoreBarProps {
  value: ScoreValue;
  max?: number;
  label?: string;
}

function isValidScore(value: ScoreValue): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function normalizeMax(max: number | undefined): number {
  return typeof max === "number" && Number.isFinite(max) && max > 0 ? max : 100;
}

function clampPercent(value: ScoreValue, max: number | undefined): number {
  if (!isValidScore(value)) return 0;
  const safeMax = normalizeMax(max);
  return Math.max(0, Math.min(100, (value / safeMax) * 100));
}

function displayScore(value: ScoreValue): string {
  return isValidScore(value) ? String(Math.round(value)) : "—";
}

function scoreLabel(label: string | undefined, value: ScoreValue, max: number | undefined, tone: ScoreTone): string {
  const name = label ?? "Score";
  if (!isValidScore(value)) return `${name}: no score`;
  return `${name}: ${displayScore(value)} out of ${Math.round(normalizeMax(max))}, ${tone.key}`;
}

export function ScoreCircle({ value, size = 72, label, max = 100 }: ScoreCircleProps) {
  const tone = scoreToneForValue(value);
  const percent = clampPercent(value, max);
  const safeSize = Math.max(44, size);

  return (
    <span
      aria-label={scoreLabel(label, value, max, tone)}
      data-score-tone={tone.key}
      data-score-value={displayScore(value)}
      role="img"
      style={{
        alignItems: "center",
        background: `conic-gradient(${tone.bar} ${percent * 3.6}deg, ${tone.background} 0deg)`,
        border: `1px solid ${tone.border}`,
        borderRadius: "50%",
        color: tone.text,
        display: "inline-flex",
        fontFamily: "var(--mono)",
        fontSize: Math.max(14, Math.round(safeSize * 0.28)),
        fontWeight: 800,
        height: safeSize,
        justifyContent: "center",
        lineHeight: 1,
        position: "relative",
        width: safeSize,
      }}
    >
      <span
        style={{
          alignItems: "center",
          background: "var(--paper)",
          borderRadius: "50%",
          display: "inline-flex",
          height: "72%",
          justifyContent: "center",
          width: "72%",
        }}
      >
        {displayScore(value)}
      </span>
    </span>
  );
}

export function ScoreBar({ value, max = 100, label }: ScoreBarProps) {
  const tone = scoreToneForValue(value);
  const percent = clampPercent(value, max);
  const labelText = label ?? "Score";

  return (
    <span
      aria-label={scoreLabel(label, value, max, tone)}
      data-score-tone={tone.key}
      data-score-value={displayScore(value)}
      style={{ display: "grid", gap: 7, minWidth: 0 }}
    >
      <span style={{ alignItems: "center", display: "flex", gap: 10, justifyContent: "space-between" }}>
        {label ? <span style={{ color: "var(--ink-2)", fontSize: 12.5 }}>{labelText}</span> : null}
        <span style={{ color: tone.text, fontFamily: "var(--mono)", fontSize: 12.5, fontWeight: 800 }}>
          {displayScore(value)}
        </span>
      </span>
      <span
        aria-hidden="true"
        style={{
          background: tone.background,
          border: `1px solid ${tone.border}`,
          borderRadius: 999,
          display: "block",
          height: 8,
          overflow: "hidden",
          width: "100%",
        }}
      >
        <span
          data-testid="score-bar-fill"
          style={{
            background: tone.bar,
            display: "block",
            height: "100%",
            width: `${percent}%`,
          }}
        />
      </span>
    </span>
  );
}
