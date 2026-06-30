"use client";

import {
  type AIResilienceModifierState,
  normalizeAIResilienceModifierState,
  normalizeAIResilienceThreshold,
} from "@/lib/ai-resilience-modifier";
import { Icon, I } from "@/lib/icons";

export function AIResilienceModifierControls({
  value,
  onChange,
  disabled = false,
  idPrefix = "ai-resilience-modifier",
}: {
  value: AIResilienceModifierState;
  onChange: (value: AIResilienceModifierState) => void;
  disabled?: boolean;
  idPrefix?: string;
}) {
  const state = normalizeAIResilienceModifierState(value);
  const thresholdId = `${idPrefix}-threshold`;
  const hideFlaggedId = `${idPrefix}-hide-flagged`;
  const helperId = `${idPrefix}-helper`;

  return (
    <fieldset
      aria-describedby={helperId}
      style={{
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: 14,
        margin: 0,
        display: "grid",
        gap: 12,
      }}
    >
      <legend
        style={{
          padding: "0 6px",
          color: "var(--ink)",
          fontSize: 13,
          fontWeight: 750,
        }}
      >
        AI Resilience modifier
      </legend>
      <p id={helperId} style={{ margin: 0, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.5 }}>
        Markets below the threshold are flagged. Hide flagged markets keeps the same strategy lens and sends the existing upstream AI filter.
      </p>
      <label htmlFor={thresholdId}>
        <div className="field-label">AI Resilience threshold</div>
        <div className="input-wrap">
          <Icon d={I.sliders} />
          <input
            id={thresholdId}
            type="number"
            min={0}
            max={100}
            step={1}
            value={state.threshold}
            disabled={disabled}
            aria-label="AI Resilience threshold"
            onChange={(event) => {
              onChange(
                normalizeAIResilienceModifierState({
                  ...state,
                  threshold: normalizeAIResilienceThreshold(event.currentTarget.valueAsNumber),
                }),
              );
            }}
          />
        </div>
      </label>
      <label
        htmlFor={hideFlaggedId}
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          color: "var(--ink-2)",
          fontSize: 13,
        }}
      >
        <input
          id={hideFlaggedId}
          type="checkbox"
          checked={state.hide_flagged}
          onChange={(event) => {
            onChange(
              normalizeAIResilienceModifierState({
                ...state,
                hide_flagged: event.currentTarget.checked,
              }),
            );
          }}
          disabled={disabled}
          style={{ accentColor: "var(--accent)" }}
        />
        Hide flagged markets
      </label>
    </fieldset>
  );
}
