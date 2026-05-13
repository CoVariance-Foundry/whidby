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

interface MetroRow {
  cbsa_code: string;
  cbsa_name: string;
  state: string;
  population: number | string | null;
  population_class: string | null;
  owner_occupancy_rate: number | string | null;
  median_household_income_usd: number | string | null;
  median_age_years: number | string | null;
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

function isMissingArchivedAtColumn(message: string | undefined): boolean {
  if (!message) return false;
  const normalized = message.toLowerCase();
  return (
    normalized.includes("archived_at") &&
    (normalized.includes("does not exist") || normalized.includes("not found"))
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

function toCachedScore(
  row: MetroScoreRow,
  reportById: Map<string, ReportRow>
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
    business_density_per_1k: null,
    establishment_growth_yoy: null,
    cached_services_count: sortedScores.length,
    best_opportunity_score: scores[0] ?? null,
    average_opportunity_score: average,
    cached_scores: sortedScores,
  };
}

export async function loadExploreData(client: SupabaseClient): Promise<ExploreData> {
  const [{ data: metroData, error: metroError }, reports] = await Promise.all([
    client
      .from("metros")
      .select(
        "cbsa_code, cbsa_name, state, population, population_class, owner_occupancy_rate, median_household_income_usd, median_age_years, principal_cities"
      )
      .order("population", { ascending: false, nullsFirst: false })
      .limit(METRO_LIMIT),
    loadReports(client),
  ]);

  if (metroError) {
    throw new Error(`loadExploreData metros: ${metroError.message}`);
  }

  const metros = (metroData ?? []) as MetroRow[];
  const reportIds = Array.from(new Set(reports.map((report) => report.id)));
  const cbsaCodes = Array.from(new Set(metros.map((metro) => metro.cbsa_code)));
  const reportById = new Map(reports.map((report) => [report.id, report]));
  const scoreRows = await loadMetroScores(client, reportIds, cbsaCodes);
  const scoresByCbsa = new Map<string, ExploreCachedScore[]>();

  for (const scoreRow of scoreRows) {
    const cachedScore = toCachedScore(scoreRow, reportById);
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
