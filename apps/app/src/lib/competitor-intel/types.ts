import type { PlanKey } from "@/lib/account/entitlements";

export const COMPETITOR_INTEL_SCAN_COST = 2;

export interface CompetitorIntelTarget {
  report_id?: string;
  city?: string;
  state?: string;
  service?: string;
  cbsa_code?: string;
  place_id?: string;
  dataforseo_location_code?: number;
}

export interface CompetitorIntelAccount {
  plan_key: PlanKey;
  plan_label: string;
  monthly_report_limit: number;
  fresh_reports_remaining: number;
}

export interface MarketLedgerItem {
  label: string;
  value: string | number | boolean | null;
  detail?: string | null;
}

export interface SummaryMetric {
  label: string;
  value: string | number | boolean | null;
  detail?: string | null;
  tone?: "neutral" | "good" | "warn" | "danger";
}

export interface CompetitorBacklink {
  domain: string;
  da?: number | null;
  anchor_text?: string | null;
}

export interface OrganicCompetitor {
  rank?: number | null;
  domain: string;
  title?: string | null;
  url?: string | null;
  domain_authority?: number | null;
  backlink_count?: number | null;
  referring_domains?: number | null;
  lighthouse_score?: number | null;
  schema_adoption?: boolean | null;
  monthly_estimated_traffic?: number | null;
  primary_keywords?: string[];
  top_backlinks?: CompetitorBacklink[];
  weaknesses?: string[];
}

export interface LocalPackCompetitor {
  rank?: number | null;
  name: string;
  rating?: number | null;
  review_count?: number | null;
  gbp_completeness?: number | null;
  website?: string | null;
  phone?: string | null;
  categories?: string[];
  weaknesses?: string[];
}

export interface WinPlanItem {
  title: string;
  play: string;
  estimated_impact?: "High" | "Medium" | "Low" | string | null;
  rationale?: string | null;
}

export interface CoverageFact {
  label: string;
  status: "available" | "partial" | "missing";
  detail?: string | null;
}

export interface CompetitorIntelReport {
  report_id?: string | null;
  city?: string | null;
  state?: string | null;
  service?: string | null;
  generated_at?: string | null;
  market_ledger: MarketLedgerItem[];
  summary_metrics: SummaryMetric[];
  organic_competitors: OrganicCompetitor[];
  local_pack_competitors: LocalPackCompetitor[];
  win_plan: WinPlanItem[];
  coverage: CoverageFact[];
}

export interface AggregateOnlyIntel {
  city?: string | null;
  state?: string | null;
  service?: string | null;
  market_ledger: MarketLedgerItem[];
  summary_metrics: SummaryMetric[];
  coverage: CoverageFact[];
  message?: string | null;
}

export type CompetitorIntelViewState =
  | { kind: "upgrade_required"; message?: string }
  | { kind: "ready_to_run"; message?: string }
  | { kind: "running"; message?: string; run_id?: string | null; report_id?: string | null }
  | { kind: "aggregate_only"; aggregate: AggregateOnlyIntel; message?: string }
  | { kind: "dossier"; report: CompetitorIntelReport; message?: string }
  | { kind: "error"; message: string };

export interface CompetitorIntelApiEnvelope {
  status?: string;
  code?: string;
  message?: string;
  run_id?: string | null;
  report_id?: string | null;
  state?: unknown;
  report?: unknown;
  dossier?: unknown;
  aggregate?: unknown;
  aggregate_only?: unknown;
  data?: unknown;
  result?: unknown;
}
