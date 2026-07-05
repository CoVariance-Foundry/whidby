import type { FullReportData, ReportMetro } from "@/lib/niche-finder/types";
import {
  getStrategyPathNode,
  type StrategyPathId,
  type StrategyPathNode,
} from "@/lib/strategies/path-registry";

export type ReportNextStepState = "available" | "locked" | "future";
export type ReportNextStepKind = "strategy" | "explore" | "competitor_intel";

export interface ReportNextStepContext {
  has_completed_scan?: boolean;
  has_ranked_site_declaration?: boolean;
}

export interface ReportNextStep {
  id: string;
  kind: ReportNextStepKind;
  title: string;
  subtitle: string;
  state: ReportNextStepState;
  primary?: boolean;
  href?: string;
  cta_label?: string;
  requirement_label?: string;
}

const DEFAULT_CONTEXT: Required<ReportNextStepContext> = {
  has_completed_scan: true,
  has_ranked_site_declaration: false,
};

const LOOKALIKE_PROFILE_KEYS = new Set([
  "expand_conquer",
  "lookalike",
  "lookalike_replication",
  "replication",
  "scale",
  "diversify_city",
]);

function strategyNode(strategyId: StrategyPathId): StrategyPathNode {
  const node = getStrategyPathNode(strategyId);
  if (!node) throw new Error(`Missing strategy path node: ${strategyId}`);
  return node;
}

function clean(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function normalizeProfile(value: string | null | undefined): string {
  return clean(value)?.toLowerCase().replace(/[\s-]+/g, "_") ?? "";
}

function stateFromReport(report: FullReportData, metro: ReportMetro): string | null {
  const source = clean(metro.cbsa_name) ?? clean(report.geo_target);
  const match = source?.match(/,\s*([A-Z]{2})(?:\b|$)/);
  return match?.[1] ?? null;
}

function appendIfPresent(params: URLSearchParams, key: string, value: string | null | undefined) {
  const trimmed = clean(value);
  if (trimmed) params.set(key, trimmed);
}

function reportContextParams(report: FullReportData, metro: ReportMetro): URLSearchParams {
  const params = new URLSearchParams();
  params.set("from_report", "1");
  appendIfPresent(params, "report_id", report.id);
  appendIfPresent(params, "city", metro.cbsa_name || report.geo_target);
  appendIfPresent(params, "service", report.niche_keyword);
  appendIfPresent(params, "cbsa_code", metro.cbsa_code);
  appendIfPresent(params, "state", stateFromReport(report, metro));
  return params;
}

function strategyHref(
  strategyId: StrategyPathId,
  report: FullReportData,
  metro: ReportMetro,
): string {
  const params = reportContextParams(report, metro);
  if (strategyId === "expand_conquer") {
    appendIfPresent(params, "reference_city_id", metro.cbsa_code || metro.cbsa_name);
  }
  return `/strategies/${strategyId}?${params.toString()}`;
}

export function buildReportExploreHref(report: FullReportData, metro: ReportMetro): string {
  const params = new URLSearchParams();
  appendIfPresent(params, "service", report.niche_keyword);
  appendIfPresent(params, "state", stateFromReport(report, metro));
  appendIfPresent(params, "from_report", "1");
  appendIfPresent(params, "report_id", report.id);
  return `/explore?${params.toString()}`;
}

export function buildReportCompetitorIntelHref(
  report: FullReportData,
  metro: ReportMetro,
): string {
  const params = new URLSearchParams();
  appendIfPresent(params, "report_id", report.id);
  appendIfPresent(params, "city", metro.cbsa_name || report.geo_target);
  appendIfPresent(params, "service", report.niche_keyword);
  appendIfPresent(params, "cbsa_code", metro.cbsa_code);
  return `/competitor-intel?${params.toString()}`;
}

function gbpBlitzStep({
  report,
  metro,
  primary,
  context,
}: {
  report: FullReportData;
  metro: ReportMetro;
  primary: boolean;
  context: Required<ReportNextStepContext>;
}): ReportNextStep {
  const node = strategyNode("gbp_blitz");
  const unlocked = node.is_runnable && context.has_completed_scan;
  return {
    id: node.strategy_id,
    kind: "strategy",
    title: `Continue to ${node.name}`,
    subtitle: unlocked
      ? "Use this completed score to tighten the Google Business Profile plan for the same market."
      : node.unlock_requirement.description,
    state: unlocked ? "available" : "locked",
    primary,
    href: unlocked ? strategyHref(node.strategy_id, report, metro) : undefined,
    cta_label: unlocked ? "Continue" : "Locked",
    requirement_label: unlocked ? undefined : node.unlock_requirement.label,
  };
}

function expandConquerStep({
  report,
  metro,
  primary,
  context,
}: {
  report: FullReportData;
  metro: ReportMetro;
  primary: boolean;
  context: Required<ReportNextStepContext>;
}): ReportNextStep {
  const node = strategyNode("expand_conquer");
  const unlocked = node.is_runnable && context.has_ranked_site_declaration;
  return {
    id: node.strategy_id,
    kind: "strategy",
    title: unlocked ? `Continue to ${node.name}` : `${node.name} requires a ranked site`,
    subtitle: unlocked
      ? "Use this market as a reference point for lookalike expansion opportunities."
      : "Declare an active ranked site before running replication or lookalike expansion guidance.",
    state: unlocked ? "available" : "locked",
    primary,
    href: unlocked ? strategyHref(node.strategy_id, report, metro) : undefined,
    cta_label: unlocked ? "Continue" : "Locked",
    requirement_label: unlocked ? undefined : node.unlock_requirement.label,
  };
}

function portfolioBuilderStep(): ReportNextStep {
  const node = strategyNode("portfolio_builder");
  return {
    id: node.strategy_id,
    kind: "strategy",
    title: node.name,
    subtitle: "Future portfolio planning node; visible for path context, but not runnable in this project.",
    state: "future",
    cta_label: "Future",
    requirement_label: node.unlock_requirement.label,
  };
}

function exploreStep(report: FullReportData, metro: ReportMetro, primary: boolean): ReportNextStep {
  return {
    id: "explore_cached",
    kind: "explore",
    title: "Browse cached markets",
    subtitle: "Return to Explore with this service context and compare cached city scores without spending fresh quota.",
    state: "available",
    primary,
    href: buildReportExploreHref(report, metro),
    cta_label: "Browse",
  };
}

function competitorIntelStep(report: FullReportData, metro: ReportMetro): ReportNextStep {
  return {
    id: "competitor_intel",
    kind: "competitor_intel",
    title: "Run Competitor Intel",
    subtitle: "See who is ranking and how to win this market. Access and quota stay enforced by the dossier route.",
    state: "available",
    href: buildReportCompetitorIntelHref(report, metro),
    cta_label: "Continue",
  };
}

export function buildReportNextSteps({
  report,
  metro,
  context,
}: {
  report: FullReportData;
  metro: ReportMetro;
  context?: ReportNextStepContext;
}): ReportNextStep[] {
  const resolvedContext: Required<ReportNextStepContext> = {
    has_completed_scan: context?.has_completed_scan ?? DEFAULT_CONTEXT.has_completed_scan,
    has_ranked_site_declaration:
      context?.has_ranked_site_declaration ?? DEFAULT_CONTEXT.has_ranked_site_declaration,
  };
  const profile = normalizeProfile(report.strategy_profile);
  const isEasyWin = profile === "easy_win";
  const isLookalikeFlow = LOOKALIKE_PROFILE_KEYS.has(profile);
  const steps: ReportNextStep[] = [];

  if (isLookalikeFlow) {
    steps.push(expandConquerStep({ report, metro, primary: true, context: resolvedContext }));
    steps.push(gbpBlitzStep({ report, metro, primary: false, context: resolvedContext }));
  } else {
    steps.push(gbpBlitzStep({ report, metro, primary: isEasyWin, context: resolvedContext }));
    steps.push(
      expandConquerStep({
        report,
        metro,
        primary: !isEasyWin && resolvedContext.has_ranked_site_declaration,
        context: resolvedContext,
      }),
    );
  }

  steps.push(exploreStep(report, metro, !steps.some((step) => step.primary)));
  steps.push(competitorIntelStep(report, metro));
  steps.push(portfolioBuilderStep());

  return steps;
}
