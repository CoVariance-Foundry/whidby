"use client";

import { Icon, I } from "@/lib/icons";
import type { SignalDefinition } from "@/lib/reports/signal-definitions";
import { formatSignalValue } from "@/lib/reports/signal-definitions";

interface Props {
  definition: SignalDefinition;
  value: unknown;
}

export default function SignalRow({ definition, value }: Props) {
  const formatted = formatSignalValue(value, definition.format);
  const isFavorable = evaluateDirection(value, definition);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr auto",
        gap: 8,
        padding: "7px 0",
        borderBottom: "1px solid var(--rule)",
        alignItems: "start",
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            fontFamily: "var(--serif)",
            fontStyle: "italic",
            fontSize: 11.5,
            color: "var(--ink-2)",
            lineHeight: 1.3,
          }}
        >
          {definition.label}
        </div>
        <div
          style={{
            fontFamily: "var(--sans)",
            fontSize: 11,
            color: "var(--ink-3)",
            lineHeight: 1.4,
            marginTop: 2,
          }}
        >
          {definition.description}
        </div>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 13,
            fontWeight: 600,
            color: "var(--ink)",
          }}
        >
          {formatted}
        </span>
        {isFavorable !== null && (
          <Icon
            d={isFavorable ? I.arrowUp : I.arrowDown}
            size={11}
            sw={2}
            style={{ color: isFavorable ? "#0f7a57" : "#a3292d" }}
          />
        )}
      </div>
    </div>
  );
}

function evaluateDirection(value: unknown, def: SignalDefinition): boolean | null {
  if (value == null) return null;
  if (def.format === "boolean") {
    const boolVal = Boolean(value);
    return def.direction === "higher_better" ? boolVal : !boolVal;
  }
  const num = Number(value);
  if (Number.isNaN(num)) return null;

  const threshold = getThreshold(def);
  if (threshold === null) return null;

  if (def.direction === "higher_better") return num >= threshold;
  return num <= threshold;
}

function getThreshold(def: SignalDefinition): number | null {
  if (def.format === "percent") return 0.5;
  if (def.format === "currency") return 5;
  if (def.format === "count") return 10;
  return 50;
}
