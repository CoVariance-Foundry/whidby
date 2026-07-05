import {
  DEFAULT_AI_RESILIENCE_MODIFIER_STATE,
  type AIResilienceModifierState,
  normalizeAIResilienceModifierState,
} from "@/lib/ai-resilience-modifier";
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

export interface ReportGuidanceEvidence {
  narrative: string[];
  actionItems: string[];
  evidence: string[];
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function normalizeBoolean(value: unknown): boolean | undefined {
  if (typeof value === "boolean") return value;
  if (typeof value === "number" && Number.isFinite(value)) return value !== 0;
  if (typeof value !== "string") return undefined;

  const normalized = value.trim().toLowerCase();
  if (["true", "1", "yes", "on"].includes(normalized)) return true;
  if (["false", "0", "no", "off"].includes(normalized)) return false;
  return undefined;
}

function modifierInputFromRecord(
  record: Record<string, unknown> | null,
): Partial<AIResilienceModifierState> | null {
  if (!record) return null;

  const threshold = record.threshold ?? record.ai_resilience_threshold;
  const hideFlagged = normalizeBoolean(record.hide_flagged ?? record.ai_resilience_filter);
  const input: Partial<AIResilienceModifierState> = {};

  if (threshold != null) input.threshold = Number(threshold);
  if (hideFlagged != null) input.hide_flagged = hideFlagged;

  return Object.keys(input).length > 0 ? input : null;
}

function reportModifierInput(report: FullReportData): Partial<AIResilienceModifierState> | null {
  const meta = asRecord(report.meta);
  const sourceContext = asRecord(meta?.source_context);
  const userState = asRecord(meta?.user_state);

  return (
    modifierInputFromRecord(asRecord(meta?.modifier_state)) ??
    modifierInputFromRecord(asRecord(meta?.ai_resilience_modifier_state)) ??
    modifierInputFromRecord(asRecord(meta?.ai_resilience_modifier)) ??
    modifierInputFromRecord(asRecord(sourceContext?.modifier_state)) ??
    modifierInputFromRecord(asRecord(userState?.ai_resilience_modifier)) ??
    modifierInputFromRecord(meta)
  );
}

function normalizeText(value: unknown): string | null {
  return typeof value === "string" ? value.trim() || null : null;
}

function normalizeTextList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map(normalizeText).filter((item): item is string => Boolean(item));
  }
  const item = normalizeText(value);
  return item ? [item] : [];
}

function uniqueStrings(values: string[]): string[] {
  const seen = new Set<string>();
  return values.filter((value) => {
    if (seen.has(value)) return false;
    seen.add(value);
    return true;
  });
}

export function normalizeReportGuidanceEvidence(
  guidance: ReportMetro["guidance"] | null | undefined,
): ReportGuidanceEvidence {
  const record = asRecord(guidance);
  if (!record) {
    return { narrative: [], actionItems: [], evidence: [] };
  }

  const generated = asRecord(record.guidance);
  const narrative = uniqueStrings(
    [
      normalizeText(record.summary),
      normalizeText(generated?.["headline"]),
      normalizeText(generated?.["strategy"]),
      normalizeText(generated?.["ai_resilience_note"]),
    ].filter((item): item is string => Boolean(item)),
  );
  const actionItems = uniqueStrings([
    ...normalizeTextList(record.action_items),
    ...normalizeTextList(generated?.["priority_actions"]),
  ]);

  return {
    narrative,
    actionItems,
    evidence: uniqueStrings([...narrative, ...actionItems]),
  };
}

function normalizeScore(value: unknown): number | null {
  if (value == null) return null;
  if (typeof value === "string" && !value.trim()) return null;
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeWarning(value: unknown): string | null {
  if (typeof value === "string") return value.trim() || null;
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  const warning =
    record.code ?? record.message ?? record.label ?? record.description ?? null;
  return typeof warning === "string" ? warning.trim() || null : null;
}

function normalizeWarnings(values: unknown): string[] {
  if (!Array.isArray(values)) return [];
  return values.map(normalizeWarning).filter((value): value is string => Boolean(value));
}

function humanizeToken(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function userFacingStrategyProfileLabel(value: string | null | undefined): string | null {
  if (!value?.trim()) return null;
  const normalized = value.trim().toLowerCase();
  if (normalized === "balanced") return "Standard scoring";
  if (normalized === "auto") return "Adaptive scoring";
  return humanizeToken(value);
}

export function reportHref(reportId: string | null | undefined): string | null {
  if (!reportId?.trim()) return null;
  return `/reports?open=${encodeURIComponent(reportId.trim())}`;
}

export function fullReportHref(reportId: string | null | undefined): string | null {
  if (!reportId?.trim()) return null;
  return `/reports/${encodeURIComponent(reportId.trim())}`;
}

export function resolveReportAIResilienceModifierState(
  report: FullReportData,
): AIResilienceModifierState {
  return normalizeAIResilienceModifierState(
    reportModifierInput(report) ?? DEFAULT_AI_RESILIENCE_MODIFIER_STATE,
  );
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
    warnings: normalizeWarnings(warnings),
    report_href: fullReportHref(reportId),
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
  modifierState = resolveReportAIResilienceModifierState(report),
}: {
  report: FullReportData;
  metro: ReportMetro;
  reportHref?: string | null;
  modifierState?: AIResilienceModifierState | null;
}): StrategyResultSummaryDto {
  const guidanceEvidence = normalizeReportGuidanceEvidence(metro.guidance);

  return {
    id: `${report.id}:${metro.cbsa_code}`,
    title: `${report.niche_keyword} in ${metro.cbsa_name}`,
    subtitle: "Top report opportunity",
    score: normalizeScore(metro.scores.opportunity),
    score_label: "Opportunity score",
    verdict: metro.difficulty_tier ?? null,
    confidence_score: normalizeScore(metro.scores.confidence?.score),
    ai_resilience_score: normalizeScore(metro.scores.ai_resilience),
    evidence: guidanceEvidence.evidence,
    warnings: normalizeWarnings(metro.scores.confidence?.flags),
    report_href: href,
    source_context: {
      strategy_id: report.strategy_profile,
      strategy_name: userFacingStrategyProfileLabel(report.strategy_profile),
      city: metro.cbsa_name,
      service: report.niche_keyword,
      segment: report.report_depth,
      modifier_state: modifierState,
    },
  };
}
