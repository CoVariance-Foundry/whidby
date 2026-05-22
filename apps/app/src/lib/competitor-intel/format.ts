import type {
  AggregateOnlyIntel,
  CompetitorBacklink,
  CompetitorIntelApiEnvelope,
  CompetitorIntelReport,
  CompetitorIntelTarget,
  CompetitorIntelViewState,
  CoverageFact,
  LocalPackCompetitor,
  MarketLedgerItem,
  OrganicCompetitor,
  SummaryMetric,
  WinPlanItem,
} from "./types";

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as UnknownRecord)
    : {};
}

function firstRecord(record: UnknownRecord, keys: string[]): UnknownRecord {
  for (const key of keys) {
    const value = record[key];
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return value as UnknownRecord;
    }
  }
  return {};
}

function readString(record: UnknownRecord, keys: string[], fallback = ""): string {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number" && Number.isFinite(value)) return String(value);
  }
  return fallback;
}

function readNullableString(record: UnknownRecord, keys: string[]): string | null {
  const value = readString(record, keys);
  return value || null;
}

function readNumber(record: UnknownRecord, keys: string[]): number | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) {
      return Number(value);
    }
  }
  return null;
}

function readBoolean(record: UnknownRecord, keys: string[]): boolean | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "boolean") return value;
    if (typeof value === "string") {
      if (value.toLowerCase() === "true") return true;
      if (value.toLowerCase() === "false") return false;
    }
  }
  return null;
}

function readStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (typeof item === "string") return item.trim();
      const record = asRecord(item);
      return readString(record, ["label", "title", "message", "description", "keyword"]);
    })
    .filter(Boolean);
}

function readArray(record: UnknownRecord, keys: string[]): unknown[] {
  for (const key of keys) {
    const value = record[key];
    if (Array.isArray(value)) return value;
  }
  return [];
}

export function hasTarget(target: CompetitorIntelTarget): boolean {
  return Boolean(
    target.report_id ||
      ((target.city || target.cbsa_code) && target.service),
  );
}

export function canRunTarget(target: CompetitorIntelTarget): boolean {
  return hasTarget(target);
}

export function buildCompetitorIntelQuery(target: CompetitorIntelTarget): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(target)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  return params.toString();
}

export function competitorIntelRunPayload(target: CompetitorIntelTarget) {
  return {
    ...target,
    scan_cost: 2,
  };
}

export function formatInteger(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Missing";
  return new Intl.NumberFormat("en-US").format(Math.round(value));
}

export function formatPercent(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Missing";
  const normalized = value <= 1 ? value * 100 : value;
  return `${Math.round(normalized)}%`;
}

export function formatBoolean(value: boolean | null | undefined): string {
  if (value === true) return "Yes";
  if (value === false) return "No";
  return "Missing";
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "Pending";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Pending";
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function formatTargetLabel(target: CompetitorIntelTarget): string {
  const service = target.service ?? "Selected service";
  const place = [target.city, target.state].filter(Boolean).join(", ");
  if (place) return `${service} in ${place}`;
  if (target.report_id) return `Report ${target.report_id}`;
  return "Choose a market";
}

export function displayValue(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined || value === "") return "Missing";
  if (typeof value === "number") return formatInteger(value);
  if (typeof value === "boolean") return formatBoolean(value);
  return value;
}

function normalizeLedgerItem(item: unknown): MarketLedgerItem | null {
  const record = asRecord(item);
  const label = readString(record, ["label", "name", "metric", "key"]);
  if (!label) return null;
  return {
    label,
    value: record.value as string | number | boolean | null,
    detail: readNullableString(record, ["detail", "description", "note"]),
  };
}

function normalizeMetric(item: unknown): SummaryMetric | null {
  const record = asRecord(item);
  const label = readString(record, ["label", "name", "metric", "key"]);
  if (!label) return null;
  const tone = readString(record, ["tone"]) as SummaryMetric["tone"];
  return {
    label,
    value: record.value as string | number | boolean | null,
    detail: readNullableString(record, ["detail", "description", "note"]),
    tone: ["neutral", "good", "warn", "danger"].includes(tone ?? "") ? tone : "neutral",
  };
}

function normalizeBacklink(item: unknown): CompetitorBacklink | null {
  const record = asRecord(item);
  const domain = readString(record, ["domain", "source", "host"]);
  if (!domain) return null;
  return {
    domain,
    da: readNumber(record, ["da", "domain_authority"]),
    anchor_text: readNullableString(record, ["anchor_text", "anchorText", "anchor"]),
  };
}

function normalizeOrganicCompetitor(item: unknown, index: number): OrganicCompetitor | null {
  const record = asRecord(item);
  const domain = readString(record, ["domain", "host", "site", "url"]);
  if (!domain) return null;
  return {
    rank: readNumber(record, ["rank", "position"]) ?? index + 1,
    domain,
    title: readNullableString(record, ["title", "name"]),
    url: readNullableString(record, ["url", "link"]),
    domain_authority: readNumber(record, ["domain_authority", "domainAuthority", "da"]),
    backlink_count: readNumber(record, ["backlink_count", "backlinkCount", "backlinks"]),
    referring_domains: readNumber(record, ["referring_domains", "referringDomains"]),
    lighthouse_score: readNumber(record, ["lighthouse_score", "lighthouseScore"]),
    schema_adoption: readBoolean(record, ["schema_adoption", "schemaAdoption", "has_schema"]),
    monthly_estimated_traffic: readNumber(record, [
      "monthly_estimated_traffic",
      "monthlyEstimatedTraffic",
      "estimated_traffic",
    ]),
    primary_keywords: readStringArray(record.primary_keywords ?? record.primaryKeywords),
    top_backlinks: readArray(record, ["top_backlinks", "topBacklinks"])
      .map(normalizeBacklink)
      .filter(Boolean) as CompetitorBacklink[],
    weaknesses: readStringArray(record.weaknesses),
  };
}

function normalizeLocalPackCompetitor(item: unknown, index: number): LocalPackCompetitor | null {
  const record = asRecord(item);
  const name = readString(record, ["name", "title", "business_name", "domain"]);
  if (!name) return null;
  return {
    rank: readNumber(record, ["rank", "position"]) ?? index + 1,
    name,
    rating: readNumber(record, ["rating", "avg_rating", "avgReview"]),
    review_count: readNumber(record, ["review_count", "reviews", "reviewCount"]),
    gbp_completeness: readNumber(record, ["gbp_completeness", "gbpCompleteness"]),
    website: readNullableString(record, ["website", "url"]),
    phone: readNullableString(record, ["phone"]),
    categories: readStringArray(record.categories),
    weaknesses: readStringArray(record.weaknesses),
  };
}

function normalizeWinPlanItem(item: unknown): WinPlanItem | null {
  const record = asRecord(item);
  const title = readString(record, ["title", "name"]);
  const play = readString(record, ["play", "description", "action"]);
  if (!title || !play) return null;
  return {
    title,
    play,
    estimated_impact: readNullableString(record, [
      "estimated_impact",
      "estimatedImpact",
      "impact",
    ]),
    rationale: readNullableString(record, ["rationale", "why"]),
  };
}

function normalizeCoverageFact(item: unknown): CoverageFact | null {
  const record = asRecord(item);
  const label = readString(record, ["label", "name", "fact", "key"]);
  if (!label) return null;
  const status = readString(record, ["status"], "available");
  return {
    label,
    status: status === "missing" || status === "partial" ? status : "available",
    detail: readNullableString(record, ["detail", "message", "description", "reason"]),
  };
}

function deriveCoverage(report: UnknownRecord): CoverageFact[] {
  const explicit = readArray(report, ["coverage", "coverage_facts", "missing_facts"])
    .map(normalizeCoverageFact)
    .filter(Boolean) as CoverageFact[];
  if (explicit.length > 0) return explicit;

  const organic = readArray(report, ["organic_competitors", "organicCompetitors", "topCompetitors"]);
  const local = readArray(report, ["local_pack_competitors", "localPackCompetitors"]);
  const winPlan = readArray(report, ["win_plan", "how_to_win", "howToWin"]);
  return [
    {
      label: "Organic SERP competitors",
      status: organic.length > 0 ? "available" : "missing",
      detail: organic.length > 0 ? `${organic.length} ranked competitors` : "No organic competitor rows returned.",
    },
    {
      label: "Local pack competitors",
      status: local.length > 0 ? "available" : "missing",
      detail: local.length > 0 ? `${local.length} local pack rows` : "No local pack evidence returned.",
    },
    {
      label: "Win plan",
      status: winPlan.length > 0 ? "available" : "missing",
      detail: winPlan.length > 0 ? `${winPlan.length} recommended plays` : "No playbook was generated.",
    },
  ];
}

function deriveSummaryMetrics(report: UnknownRecord): SummaryMetric[] {
  const explicit = readArray(report, ["summary_metrics", "summaryMetrics", "metrics"])
    .map(normalizeMetric)
    .filter(Boolean) as SummaryMetric[];
  if (explicit.length > 0) return explicit;

  const summary = firstRecord(report, ["summary"]);
  const metrics: SummaryMetric[] = [];
  const avgDa = readNumber(summary, ["avgDa", "avg_da", "avg_domain_authority"]);
  const avgBacklinks = readNumber(summary, ["avgBacklinks", "avg_backlinks"]);
  const avgReviews = readNumber(summary, ["avgReviews", "avg_reviews"]);
  const schema = readNumber(summary, ["avgSchemaAdoption", "avg_schema_adoption"]);

  if (avgDa !== null) metrics.push({ label: "Avg DA", value: avgDa, detail: "Top local organic domains" });
  if (avgBacklinks !== null) metrics.push({ label: "Avg backlinks", value: avgBacklinks });
  if (avgReviews !== null) metrics.push({ label: "Avg reviews", value: avgReviews });
  if (schema !== null) metrics.push({ label: "Schema adoption", value: formatPercent(schema) });
  return metrics;
}

function deriveLedger(report: UnknownRecord): MarketLedgerItem[] {
  const explicit = readArray(report, ["market_ledger", "marketLedger", "ledger"])
    .map(normalizeLedgerItem)
    .filter(Boolean) as MarketLedgerItem[];
  if (explicit.length > 0) return explicit;

  return [
    { label: "Market", value: [readString(report, ["city"]), readString(report, ["state"])].filter(Boolean).join(", ") || null },
    { label: "Service", value: readNullableString(report, ["service", "niche"]) },
    { label: "Generated", value: formatDate(readNullableString(report, ["generated_at", "generatedAt"])) },
    { label: "Report", value: readNullableString(report, ["report_id", "reportId", "id"]) },
  ];
}

export function normalizeCompetitorIntelReport(value: unknown): CompetitorIntelReport {
  const report = asRecord(value);
  return {
    report_id: readNullableString(report, ["report_id", "reportId", "id"]),
    city: readNullableString(report, ["city"]),
    state: readNullableString(report, ["state", "region"]),
    service: readNullableString(report, ["service", "niche"]),
    generated_at: readNullableString(report, ["generated_at", "generatedAt"]),
    market_ledger: deriveLedger(report),
    summary_metrics: deriveSummaryMetrics(report),
    organic_competitors: readArray(report, [
      "organic_competitors",
      "organicCompetitors",
      "top_organic_competitors",
      "topCompetitors",
    ]).map(normalizeOrganicCompetitor).filter(Boolean) as OrganicCompetitor[],
    local_pack_competitors: readArray(report, [
      "local_pack_competitors",
      "localPackCompetitors",
      "maps_competitors",
    ]).map(normalizeLocalPackCompetitor).filter(Boolean) as LocalPackCompetitor[],
    win_plan: readArray(report, ["win_plan", "how_to_win", "howToWin", "plays"])
      .map(normalizeWinPlanItem)
      .filter(Boolean) as WinPlanItem[],
    coverage: deriveCoverage(report),
  };
}

export function normalizeAggregateOnly(value: unknown): AggregateOnlyIntel {
  const aggregate = asRecord(value);
  return {
    city: readNullableString(aggregate, ["city"]),
    state: readNullableString(aggregate, ["state", "region"]),
    service: readNullableString(aggregate, ["service", "niche"]),
    market_ledger: deriveLedger(aggregate),
    summary_metrics: deriveSummaryMetrics(aggregate),
    coverage: deriveCoverage(aggregate),
    message: readNullableString(aggregate, ["message"]),
  };
}

export function normalizeCompetitorIntelState(
  envelope: CompetitorIntelApiEnvelope,
): CompetitorIntelViewState {
  const status = envelope.status ?? asRecord(envelope.state).kind;
  if (status === "succeeded" && envelope.result) {
    return normalizeCompetitorIntelState(
      asRecord(envelope.result) as CompetitorIntelApiEnvelope,
    );
  }
  const payload = envelope.report ?? envelope.dossier ?? envelope.data;

  if (status === "upgrade_required" || status === "tier_limit") {
    return {
      kind: "upgrade_required",
      message: envelope.message ?? "Competitor Intel requires Plus or Pro.",
    };
  }
  if (status === "ready_to_run") {
    return { kind: "ready_to_run", message: envelope.message };
  }
  if (status === "running" || status === "queued" || status === "pending") {
    return {
      kind: "running",
      message: envelope.message ?? "Competitor Intel is running.",
      run_id: envelope.run_id ?? null,
      report_id: envelope.report_id ?? null,
    };
  }
  if (status === "aggregate_only" || envelope.aggregate || envelope.aggregate_only) {
    return {
      kind: "aggregate_only",
      aggregate: normalizeAggregateOnly(envelope.aggregate ?? envelope.aggregate_only ?? envelope.data),
      message: envelope.message,
    };
  }
  if (status === "error" || status === "validation_error" || status === "quota_exceeded") {
    return { kind: "error", message: envelope.message ?? "Competitor Intel is unavailable." };
  }
  if (payload) {
    return {
      kind: "dossier",
      report: normalizeCompetitorIntelReport(payload),
      message: envelope.message,
    };
  }
  return { kind: "ready_to_run", message: envelope.message };
}
