import type { SupabaseClient } from "@supabase/supabase-js";
import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";
import { deriveArchetype } from "@/lib/niche-finder/derive-archetype";
import type {
  ExploreCachedScore,
  ExploreCitySummary,
  ExploreData,
} from "./types";

const METRO_LIMIT = 100;
const REPORT_LIMIT = 500;
const SCORE_LIMIT = 500;
const SCORE_REPORT_BATCH_SIZE = 100;
const FRESHNESS_REPORT_BATCH_SIZE = 100;
const FRESHNESS_TARGET_BATCH_SIZE = 100;
const DEFAULT_STALE_AFTER_DAYS = 30;
const BASE_METRO_SELECT =
  "cbsa_code, cbsa_name, state, population, population_class, owner_occupancy_rate, median_household_income_usd, median_age_years, principal_cities";
const OPTIONAL_METRO_METRIC_COLUMNS = [
  "business_density_per_1k",
  "establishment_growth_yoy",
] as const;
const COMPLETE_METRO_SELECT = `${BASE_METRO_SELECT}, ${OPTIONAL_METRO_METRIC_COLUMNS.join(", ")}`;

interface MetroRow {
  cbsa_code: string;
  cbsa_name: string;
  state: string;
  population: number | string | null;
  population_class: string | null;
  owner_occupancy_rate: number | string | null;
  median_household_income_usd: number | string | null;
  median_age_years: number | string | null;
  business_density_per_1k?: number | string | null;
  establishment_growth_yoy?: number | string | null;
  principal_cities?: unknown;
}

interface ReportRow {
  id: string;
  created_at: string;
  niche_keyword: string;
  geo_target?: string | null;
  metros?: unknown;
}

interface MetroScoreRow {
  report_id: string;
  cbsa_code: string;
  opportunity_score: number | string | null;
  serp_archetype: string | null;
  ai_exposure: string | null;
  difficulty_tier: string | null;
  confidence_score?: number | string | null;
  ai_resilience_score?: number | string | null;
}

interface LatestTargetScoreRow {
  target_id: string | null;
  report_id: string;
  cbsa_code: string;
  scored_at: string | null;
  opportunity_score: number | string | null;
}

interface TargetTrendRow {
  target_id: string | null;
  report_id: string;
  cbsa_code: string;
  scored_at: string | null;
  opportunity_delta: number | string | null;
}

interface RefreshTargetRow {
  id: string;
  next_refresh_at: string | null;
}

interface ScoreFreshness {
  refresh_target_id: string;
  last_refreshed_at: string;
  next_refresh_at?: string;
  stale_after_days: number;
  is_stale: boolean;
  opportunity_delta: number | null;
}

function isMissingArchivedAtColumn(message: string | undefined): boolean {
  if (!message) return false;
  const normalized = message.toLowerCase();
  return (
    normalized.includes("archived_at") &&
    (normalized.includes("does not exist") || normalized.includes("not found"))
  );
}

function isMissingRefreshSource(
  message: string | undefined,
  sourceName: string
): boolean {
  if (!message) return false;
  const normalized = message.toLowerCase();
  const source = sourceName.toLowerCase();
  const mentionsSource =
    normalized.includes(source) || normalized.includes(`public.${source}`);

  if (!mentionsSource || normalized.includes("column ")) return false;
  if (normalized.includes("permission denied")) return true;
  if (normalized.includes("schema cache")) return true;
  if (normalized.includes("could not find")) return true;
  if (normalized.includes("not found")) return true;

  return normalized.includes("does not exist");
}

function isMissingOptionalMetroMetricColumn(message: string | undefined): boolean {
  if (!message) return false;
  const normalized = message.toLowerCase();
  const mentionsOptionalMetric = OPTIONAL_METRO_METRIC_COLUMNS.some((column) =>
    normalized.includes(column)
  );
  if (!mentionsOptionalMetric) return false;

  return (
    normalized.includes("schema cache") ||
    normalized.includes("does not exist") ||
    normalized.includes("not found") ||
    normalized.includes("could not find")
  );
}

function asNumber(value: number | string | null | undefined): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function optionalNumber(value: number | string | null | undefined): number | undefined {
  return asNumber(value) ?? undefined;
}

function optionalText(value: string | null | undefined): string | undefined {
  return value?.trim() ? value : undefined;
}

function scoreKey(reportId: string, cbsaCode: string): string {
  return `${reportId}:${cbsaCode}`;
}

function toTimestamp(value: string | null | undefined): number | null {
  if (!value) return null;
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function computeIsStale(
  lastRefreshedAt: string,
  nextRefreshAt: string | undefined,
  staleAfterDays: number
): boolean {
  const now = Date.now();
  const nextRefreshTimestamp = toTimestamp(nextRefreshAt);
  if (nextRefreshTimestamp !== null) {
    return nextRefreshTimestamp <= now;
  }

  const lastRefreshedTimestamp = toTimestamp(lastRefreshedAt);
  if (lastRefreshedTimestamp === null) return false;

  const staleTimestamp =
    lastRefreshedTimestamp + staleAfterDays * 24 * 60 * 60 * 1000;
  return staleTimestamp <= now;
}

const BACKEND_ARCHETYPE_MAP: Record<string, ArchetypeId> = {
  AGGREGATOR_DOMINATED: "AGG",
  LOCAL_PACK_FORTIFIED: "PACK_FORT",
  LOCAL_PACK_ESTABLISHED: "PACK_EST",
  LOCAL_PACK_VULNERABLE: "PACK_VULN",
  FRAGMENTED_WEAK: "FRAG_WEAK",
  FRAGMENTED_COMPETITIVE: "FRAG_COMP",
  BARREN: "BARREN",
  MIXED: "MIXED",
};

function archetypeFromScore(row: MetroScoreRow): ArchetypeId {
  const raw = row.serp_archetype?.trim();
  if (raw) {
    const mapped = BACKEND_ARCHETYPE_MAP[raw.toUpperCase()];
    if (mapped) return mapped;
    if (ARCHETYPES.some((a) => a.id === raw)) {
      return raw as ArchetypeId;
    }
  }
  return deriveArchetype({ opportunity_score: asNumber(row.opportunity_score) });
}

function archetypeLabel(id: ArchetypeId): string {
  return ARCHETYPES.find((a) => a.id === id)?.short ?? "Mixed";
}

async function loadReports(client: SupabaseClient): Promise<ReportRow[]> {
  let { data, error } = await client
    .from("reports")
    .select("id, created_at, niche_keyword, geo_target, metros")
    .is("archived_at", null)
    .order("created_at", { ascending: false })
    .limit(REPORT_LIMIT);

  if (isMissingArchivedAtColumn(error?.message)) {
    ({ data, error } = await client
      .from("reports")
      .select("id, created_at, niche_keyword, geo_target, metros")
      .order("created_at", { ascending: false })
      .limit(REPORT_LIMIT));
  }

  if (error) {
    throw new Error(`loadExploreData reports: ${error.message}`);
  }

  return (data ?? []) as ReportRow[];
}

async function loadMetros(client: SupabaseClient): Promise<MetroRow[]> {
  let { data, error } = await client
    .from("metros")
    .select(COMPLETE_METRO_SELECT)
    .order("population", { ascending: false, nullsFirst: false })
    .limit(METRO_LIMIT);

  if (isMissingOptionalMetroMetricColumn(error?.message)) {
    ({ data, error } = await client
      .from("metros")
      .select(BASE_METRO_SELECT)
      .order("population", { ascending: false, nullsFirst: false })
      .limit(METRO_LIMIT));
  }

  if (error) {
    throw new Error(`loadExploreData metros: ${error.message}`);
  }

  return (data ?? []) as MetroRow[];
}

async function loadMetroScores(
  client: SupabaseClient,
  reportIds: string[],
  cbsaCodes: string[]
): Promise<MetroScoreRow[]> {
  if (reportIds.length === 0 || cbsaCodes.length === 0) return [];

  const rows: MetroScoreRow[] = [];

  for (
    let index = 0;
    index < reportIds.length && rows.length < SCORE_LIMIT;
    index += SCORE_REPORT_BATCH_SIZE
  ) {
    const remaining = SCORE_LIMIT - rows.length;
    const reportIdsBatch = reportIds.slice(index, index + SCORE_REPORT_BATCH_SIZE);

    const { data, error } = await client
      .from("metro_scores")
      .select(
        "report_id, cbsa_code, opportunity_score, serp_archetype, ai_exposure, difficulty_tier, confidence_score, ai_resilience_score"
      )
      .in("report_id", reportIdsBatch)
      .in("cbsa_code", cbsaCodes)
      .order("cbsa_code", { ascending: true })
      .limit(remaining);

    if (error) {
      throw new Error(`loadExploreData metro_scores: ${error.message}`);
    }

    rows.push(...((data ?? []) as MetroScoreRow[]).slice(0, remaining));
  }

  return rows;
}

async function loadLatestTargetScores(
  client: SupabaseClient,
  reportIds: string[],
  cbsaCodes: string[]
): Promise<LatestTargetScoreRow[] | null> {
  if (reportIds.length === 0 || cbsaCodes.length === 0) return [];

  const rows: LatestTargetScoreRow[] = [];

  for (
    let index = 0;
    index < reportIds.length && rows.length < SCORE_LIMIT;
    index += FRESHNESS_REPORT_BATCH_SIZE
  ) {
    const remaining = SCORE_LIMIT - rows.length;
    const reportIdsBatch = reportIds.slice(
      index,
      index + FRESHNESS_REPORT_BATCH_SIZE
    );

    const { data, error } = await client
      .from("explore_latest_target_scores")
      .select("target_id, report_id, cbsa_code, scored_at, opportunity_score")
      .in("report_id", reportIdsBatch)
      .in("cbsa_code", cbsaCodes)
      .order("scored_at", { ascending: false })
      .limit(remaining);

    if (error) {
      if (isMissingRefreshSource(error.message, "explore_latest_target_scores")) {
        return null;
      }
      throw new Error(
        `loadExploreData explore_latest_target_scores: ${error.message}`
      );
    }

    rows.push(...((data ?? []) as LatestTargetScoreRow[]).slice(0, remaining));
  }

  return rows;
}

async function loadTargetTrendRows(
  client: SupabaseClient,
  reportIds: string[],
  cbsaCodes: string[],
  targetIds: string[]
): Promise<TargetTrendRow[] | null> {
  if (targetIds.length === 0) return [];

  const rows: TargetTrendRow[] = [];

  for (
    let targetIndex = 0;
    targetIndex < targetIds.length && rows.length < SCORE_LIMIT;
    targetIndex += FRESHNESS_TARGET_BATCH_SIZE
  ) {
    const targetIdsBatch = targetIds.slice(
      targetIndex,
      targetIndex + FRESHNESS_TARGET_BATCH_SIZE
    );

    for (
      let reportIndex = 0;
      reportIndex < reportIds.length && rows.length < SCORE_LIMIT;
      reportIndex += FRESHNESS_REPORT_BATCH_SIZE
    ) {
      const remaining = SCORE_LIMIT - rows.length;
      const reportIdsBatch = reportIds.slice(
        reportIndex,
        reportIndex + FRESHNESS_REPORT_BATCH_SIZE
      );

      const { data, error } = await client
        .from("explore_target_trends")
        .select("target_id, report_id, cbsa_code, scored_at, opportunity_delta")
        .in("target_id", targetIdsBatch)
        .in("report_id", reportIdsBatch)
        .in("cbsa_code", cbsaCodes)
        .order("scored_at", { ascending: false })
        .limit(remaining);

      if (error) {
        if (isMissingRefreshSource(error.message, "explore_target_trends")) {
          return null;
        }
        throw new Error(`loadExploreData explore_target_trends: ${error.message}`);
      }

      rows.push(...((data ?? []) as TargetTrendRow[]).slice(0, remaining));
    }
  }

  return rows;
}

async function loadRefreshTargetRows(
  client: SupabaseClient,
  targetIds: string[]
): Promise<RefreshTargetRow[]> {
  if (targetIds.length === 0) return [];

  const rows: RefreshTargetRow[] = [];

  for (
    let index = 0;
    index < targetIds.length;
    index += FRESHNESS_TARGET_BATCH_SIZE
  ) {
    const targetIdsBatch = targetIds.slice(
      index,
      index + FRESHNESS_TARGET_BATCH_SIZE
    );

    const { data, error } = await client
      .from("explore_refresh_targets")
      .select("id, next_refresh_at")
      .in("id", targetIdsBatch)
      .limit(targetIdsBatch.length);

    if (error) {
      if (isMissingRefreshSource(error.message, "explore_refresh_targets")) {
        return [];
      }
      throw new Error(`loadExploreData explore_refresh_targets: ${error.message}`);
    }

    rows.push(...((data ?? []) as RefreshTargetRow[]));
  }

  return rows;
}

async function loadScoreFreshness(
  client: SupabaseClient,
  scoreRows: MetroScoreRow[]
): Promise<Map<string, ScoreFreshness>> {
  if (scoreRows.length === 0) return new Map();

  const reportIds = Array.from(new Set(scoreRows.map((row) => row.report_id)));
  const cbsaCodes = Array.from(new Set(scoreRows.map((row) => row.cbsa_code)));
  const latestRows = await loadLatestTargetScores(client, reportIds, cbsaCodes);
  if (!latestRows || latestRows.length === 0) return new Map();

  const targetIds = Array.from(
    new Set(
      latestRows
        .map((row) => row.target_id)
        .filter((targetId): targetId is string => Boolean(targetId))
    )
  );
  const latestReportIds = Array.from(new Set(latestRows.map((row) => row.report_id)));
  const [trendRows, targetRows] = await Promise.all([
    loadTargetTrendRows(client, latestReportIds, cbsaCodes, targetIds),
    loadRefreshTargetRows(client, targetIds),
  ]);

  const trendsByScore = new Map<string, TargetTrendRow>();

  for (const trendRow of trendRows ?? []) {
    const key = scoreKey(trendRow.report_id, trendRow.cbsa_code);
    const current = trendsByScore.get(key);
    if (!current || (trendRow.scored_at ?? "") > (current.scored_at ?? "")) {
      trendsByScore.set(key, trendRow);
    }
  }

  const targetById = new Map(targetRows.map((row) => [row.id, row]));
  const freshnessByScore = new Map<string, ScoreFreshness>();

  for (const latestRow of latestRows) {
    if (!latestRow.target_id || !latestRow.scored_at) continue;

    const key = scoreKey(latestRow.report_id, latestRow.cbsa_code);
    const current = freshnessByScore.get(key);
    if (current && latestRow.scored_at <= current.last_refreshed_at) continue;

    const target = targetById.get(latestRow.target_id);
    const nextRefreshAt = target?.next_refresh_at ?? undefined;
    const staleAfterDays = DEFAULT_STALE_AFTER_DAYS;
    const trend = trendsByScore.get(key);

    const freshness: ScoreFreshness = {
      refresh_target_id: latestRow.target_id,
      last_refreshed_at: latestRow.scored_at,
      stale_after_days: staleAfterDays,
      is_stale: computeIsStale(
        latestRow.scored_at,
        nextRefreshAt,
        staleAfterDays
      ),
      opportunity_delta:
        trend && trend.opportunity_delta !== null
          ? asNumber(trend.opportunity_delta)
          : null,
    };

    if (nextRefreshAt) {
      freshness.next_refresh_at = nextRefreshAt;
    }

    freshnessByScore.set(key, freshness);
  }

  return freshnessByScore;
}

function toCachedScore(
  row: MetroScoreRow,
  reportById: Map<string, ReportRow>,
  freshness?: ScoreFreshness
): ExploreCachedScore | null {
  const report = reportById.get(row.report_id);
  const opportunity_score = asNumber(row.opportunity_score);
  if (!report || opportunity_score === null) return null;

  const archetype_id = archetypeFromScore(row);
  return {
    report_id: row.report_id,
    service: report.niche_keyword,
    opportunity_score: Math.round(opportunity_score),
    archetype_id,
    archetype_label: archetypeLabel(archetype_id),
    last_scored_at: report.created_at,
    confidence_score: optionalNumber(row.confidence_score),
    ai_resilience_score: optionalNumber(row.ai_resilience_score),
    ai_exposure: optionalText(row.ai_exposure),
    difficulty_tier: optionalText(row.difficulty_tier),
    ...(freshness
      ? {
          refresh_target_id: freshness.refresh_target_id,
          last_refreshed_at: freshness.last_refreshed_at,
          ...(freshness.next_refresh_at
            ? { next_refresh_at: freshness.next_refresh_at }
            : {}),
          stale_after_days: freshness.stale_after_days,
          is_stale: freshness.is_stale,
          opportunity_delta: freshness.opportunity_delta,
        }
      : {}),
  };
}

function summarizeMetro(
  metro: MetroRow,
  cached_scores: ExploreCachedScore[]
): ExploreCitySummary {
  const latestByService = new Map<string, ExploreCachedScore>();

  for (const score of cached_scores) {
    const current = latestByService.get(score.service);
    if (!current || score.last_scored_at > current.last_scored_at) {
      latestByService.set(score.service, score);
    }
  }

  const sortedScores = [...latestByService.values()].sort((a, b) => {
    if (b.opportunity_score !== a.opportunity_score) {
      return b.opportunity_score - a.opportunity_score;
    }
    return b.last_scored_at.localeCompare(a.last_scored_at);
  });
  const scores = sortedScores.map((score) => score.opportunity_score);
  const average =
    scores.length > 0
      ? Math.round(scores.reduce((total, score) => total + score, 0) / scores.length)
      : null;

  return {
    cbsa_code: metro.cbsa_code,
    cbsa_name: metro.cbsa_name,
    state: metro.state,
    population: asNumber(metro.population),
    population_class: metro.population_class,
    median_household_income_usd: asNumber(metro.median_household_income_usd),
    owner_occupancy_rate: asNumber(metro.owner_occupancy_rate),
    median_age_years: asNumber(metro.median_age_years),
    business_density_per_1k: asNumber(metro.business_density_per_1k),
    establishment_growth_yoy: asNumber(metro.establishment_growth_yoy),
    cached_services_count: sortedScores.length,
    best_opportunity_score: scores[0] ?? null,
    average_opportunity_score: average,
    cached_scores: sortedScores,
  };
}

export async function loadExploreData(client: SupabaseClient): Promise<ExploreData> {
  const [metros, reports] = await Promise.all([
    loadMetros(client),
    loadReports(client),
  ]);
  const reportIds = Array.from(new Set(reports.map((report) => report.id)));
  const cbsaCodes = Array.from(new Set(metros.map((metro) => metro.cbsa_code)));
  const reportById = new Map(reports.map((report) => [report.id, report]));
  const scoreRows = await loadMetroScores(client, reportIds, cbsaCodes);
  const freshnessByScore = await loadScoreFreshness(client, scoreRows);
  const scoresByCbsa = new Map<string, ExploreCachedScore[]>();

  for (const scoreRow of scoreRows) {
    const cachedScore = toCachedScore(
      scoreRow,
      reportById,
      freshnessByScore.get(scoreKey(scoreRow.report_id, scoreRow.cbsa_code))
    );
    if (!cachedScore) continue;

    const current = scoresByCbsa.get(scoreRow.cbsa_code) ?? [];
    current.push(cachedScore);
    scoresByCbsa.set(scoreRow.cbsa_code, current);
  }

  const cities = metros
    .map((metro) => summarizeMetro(metro, scoresByCbsa.get(metro.cbsa_code) ?? []))
    .sort((a, b) => {
      const bestDelta =
        (b.best_opportunity_score ?? -1) - (a.best_opportunity_score ?? -1);
      if (bestDelta !== 0) return bestDelta;
      return (b.population ?? 0) - (a.population ?? 0);
    });

  return { cities };
}
