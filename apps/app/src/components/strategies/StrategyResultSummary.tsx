import Link from "next/link";
import type { ReactNode } from "react";
import { AIResilienceFlagBadge } from "@/components/AIResilienceFlagBadge";
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

export function StrategyResultSummary({
  summary,
  aiResilienceThreshold,
  framed = true,
  reportCtaLabel = "Open full report",
}: {
  summary: StrategyResultSummaryDto;
  aiResilienceThreshold?: number;
  framed?: boolean;
  reportCtaLabel?: string;
}) {
  const context = summary.source_context;
  const modifier = context.modifier_state;

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
          {context.strategy_id ? <ContextPill>{context.strategy_id}</ContextPill> : null}
          {context.segment ? <ContextPill>{context.segment}</ContextPill> : null}
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
            No strategy evidence returned for this row.
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
