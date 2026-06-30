import type { AIResilienceModifierState } from "@/lib/ai-resilience-modifier";
import type { FullReportData, ReportMetro } from "@/lib/niche-finder/types";

export interface StrategyResultSourceContext {
  strategy_id?: string | null;
  strategy_name?: string | null;
  city?: string | null;
  service?: string | null;
  segment?: string | null;
  modifier_state?: AIResilienceModifierState | null;
}

export interface StrategyResultSummaryDto {
  id: string;
  title: string;
  subtitle?: string | null;
  score: number | null;
  score_label: string;
  verdict?: string | null;
  confidence_score?: number | null;
  ai_resilience_score?: number | null;
  evidence: string[];
  warnings: string[];
  report_href?: string | null;
  source_context: StrategyResultSourceContext;
}

function normalizeScore(value: unknown): number | null {
  if (value == null) return null;
  if (typeof value === "string" && !value.trim()) return null;
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

export function reportHref(reportId: string | null | undefined): string | null {
  if (!reportId?.trim()) return null;
  return `/reports?open=${encodeURIComponent(reportId.trim())}`;
}

export function fullReportHref(reportId: string | null | undefined): string | null {
  if (!reportId?.trim()) return null;
  return `/reports/${encodeURIComponent(reportId.trim())}`;
}

export function createInlineStrategyResultSummary({
  id,
  city,
  service,
  rank,
  score,
  scoreLabel = "Strategy score",
  verdict = null,
  confidenceScore = null,
  aiResilienceScore = null,
  evidence = [],
  warnings = [],
  reportId = null,
  sourceContext,
}: {
  id: string;
  city: string;
  service: string;
  rank?: number | null;
  score: unknown;
  scoreLabel?: string;
  verdict?: string | null;
  confidenceScore?: unknown;
  aiResilienceScore?: unknown;
  evidence?: string[];
  warnings?: string[];
  reportId?: string | null;
  sourceContext: StrategyResultSourceContext;
}): StrategyResultSummaryDto {
  const title = `${service} in ${city}`;

  return {
    id,
    title,
    subtitle: rank ? `Rank #${rank}` : null,
    score: normalizeScore(score),
    score_label: scoreLabel,
    verdict,
    confidence_score: normalizeScore(confidenceScore),
    ai_resilience_score: normalizeScore(aiResilienceScore),
    evidence,
    warnings,
    report_href: reportHref(reportId),
    source_context: {
      ...sourceContext,
      city,
      service,
    },
  };
}

export function createReportStrategyResultSummary({
  report,
  metro,
  reportHref: href = fullReportHref(report.id),
}: {
  report: FullReportData;
  metro: ReportMetro;
  reportHref?: string | null;
}): StrategyResultSummaryDto {
  return {
    id: `${report.id}:${metro.cbsa_code}`,
    title: `${report.niche_keyword} in ${metro.cbsa_name}`,
    subtitle: "Top report opportunity",
    score: normalizeScore(metro.scores.opportunity),
    score_label: "Opportunity score",
    verdict: metro.difficulty_tier ?? null,
    confidence_score: normalizeScore(metro.scores.confidence?.score),
    ai_resilience_score: normalizeScore(metro.scores.ai_resilience),
    evidence: metro.guidance?.summary ? [metro.guidance.summary] : [],
    warnings: metro.scores.confidence?.flags ?? [],
    report_href: href,
    source_context: {
      strategy_id: report.strategy_profile,
      city: metro.cbsa_name,
      service: report.niche_keyword,
      segment: report.report_depth,
    },
  };
}
