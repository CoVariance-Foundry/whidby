import Link from "next/link";
import type { ReactNode } from "react";
import { AIResilienceFlagBadge } from "@/components/AIResilienceFlagBadge";
import type { AIResilienceModifierState } from "@/lib/ai-resilience-modifier";
import { ScoreCircle } from "@/components/ScoreVisuals";
import type { StrategyResultSummaryDto } from "@/lib/strategy-result-summary";
import { Icon, I } from "@/lib/icons";

function ContextPill({ children }: { children: ReactNode }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        minHeight: 22,
        padding: "2px 8px",
        borderRadius: 999,
        border: "1px solid var(--rule)",
        background: "var(--paper-alt)",
        color: "var(--ink-2)",
        fontSize: 11,
        fontWeight: 750,
        lineHeight: 1.4,
      }}
    >
      {children}
    </span>
  );
}

const SEGMENT_LABELS: Record<string, string> = {
  standard: "Standard report",
  deep: "Deep report",
  launch: "Launch",
  rail_step: "Path step",
  side_branch: "Side branch",
  locked_teaser: "Locked",
};

function humanizeToken(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function strategyContextLabel(context: StrategyResultSummaryDto["source_context"]) {
  if (context.strategy_name?.trim()) return context.strategy_name.trim();
  if (!context.strategy_id?.trim()) return null;
  return humanizeToken(context.strategy_id);
}

function segmentContextLabel(value: string | null | undefined) {
  if (!value?.trim()) return null;
  return SEGMENT_LABELS[value] ?? humanizeToken(value);
}

export function StrategyResultSummary({
  summary,
  aiResilienceThreshold,
  modifierState,
  framed = true,
  reportCtaLabel = "Open full report",
}: {
  summary: StrategyResultSummaryDto;
  aiResilienceThreshold?: number;
  modifierState?: AIResilienceModifierState | null;
  framed?: boolean;
  reportCtaLabel?: string;
}) {
  const context = summary.source_context;
  const modifier = modifierState ?? context.modifier_state;
  const strategyLabel = strategyContextLabel(context);
  const segmentLabel = segmentContextLabel(context.segment);

  return (
    <article
      style={{
        background: framed ? "var(--card)" : "transparent",
        border: framed ? "1px solid var(--rule)" : "0",
        borderRadius: framed ? 8 : 0,
        padding: framed ? 16 : 0,
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) auto",
        gap: 16,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {summary.subtitle ? (
            <span style={{ fontFamily: "var(--mono)", color: "var(--ink-3)", fontSize: 12 }}>
              {summary.subtitle}
            </span>
          ) : null}
          <h3 style={{ margin: 0, fontSize: 16, color: "var(--ink)" }}>{summary.title}</h3>
          <AIResilienceFlagBadge
            score={summary.ai_resilience_score}
            threshold={aiResilienceThreshold}
          />
        </div>

        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
          {strategyLabel ? <ContextPill>{strategyLabel}</ContextPill> : null}
          {segmentLabel ? <ContextPill>{segmentLabel}</ContextPill> : null}
          {summary.confidence_score != null ? (
            <ContextPill>Confidence: {Math.round(summary.confidence_score)}</ContextPill>
          ) : null}
          {modifier ? (
            <ContextPill>AI threshold: {modifier.threshold}</ContextPill>
          ) : null}
          {modifier?.hide_flagged ? <ContextPill>Hide flagged</ContextPill> : null}
        </div>

        {summary.verdict ? (
          <p style={{ margin: "10px 0 0", color: "var(--ink-2)", fontSize: 13, lineHeight: 1.5 }}>
            Verdict: {summary.verdict}
          </p>
        ) : null}

        {summary.evidence.length > 0 ? (
          <ul style={{ margin: "10px 0 0", paddingLeft: 18, color: "var(--ink-2)", fontSize: 13, lineHeight: 1.5 }}>
            {summary.evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : (
          <p style={{ margin: "10px 0 0", color: "var(--ink-3)", fontSize: 13 }}>
            No additional evidence is available for this result.
          </p>
        )}

        {summary.warnings.length > 0 ? (
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
            {summary.warnings.map((warning) => (
              <span
                key={warning}
                style={{
                  alignSelf: "flex-start",
                  color: "var(--warn)",
                  background: "var(--warn-soft)",
                  border: "1px solid var(--rule)",
                  borderRadius: 999,
                  padding: "4px 8px",
                  fontSize: 12,
                }}
              >
                {warning}
              </span>
            ))}
          </div>
        ) : null}

        {summary.report_href ? (
          <Link
            href={summary.report_href}
            className="btn-ghost"
            style={{ textDecoration: "none", marginTop: 12, width: "fit-content" }}
          >
            {reportCtaLabel} <Icon d={I.arrow} />
          </Link>
        ) : null}
      </div>

      <ScoreCircle value={summary.score} label={summary.score_label} size={68} />
    </article>
  );
}
