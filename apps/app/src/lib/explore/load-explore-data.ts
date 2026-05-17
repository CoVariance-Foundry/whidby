import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";
import { deriveArchetype } from "@/lib/niche-finder/derive-archetype";
import type {
  ExploreCachedScore,
  ExploreCitySummary,
  ExploreData,
  ExploreScoreSystem,
} from "./types";

export interface ExploreQueryParams {
  service?: string;
  states?: string[];
  state?: string | string[];
  limit?: number;
  cursor?: string;
  sort?: string;
  direction?: string;
  population_min?: number;
  population_max?: number;
  income_min?: number;
  income_max?: number;
  growing_only?: boolean;
  // Backward-compatible aliases accepted from older callers; serialized as backend names.
  min_population?: number;
  max_population?: number;
  min_income?: number;
}

type SearchParamRecord = Record<string, string | string[] | undefined>;

type BackendCachedScore = Partial<ExploreCachedScore> & {
  service?: string | null;
  niche_normalized?: string | null;
  niche_keyword?: string | null;
  score_system?: string | null;
  presentation_score?: number | string | null;
  opportunity_score?: number | string | null;
  latest_scored_at?: string | null;
  last_scored_at?: string | null;
  stale?: boolean | null;
  is_stale?: boolean;
  serp_archetype?: string | null;
  archetype_id?: string | null;
  archetype_label?: string | null;
};

type BackendCity = Partial<ExploreCitySummary> & {
  score_system?: string | null;
  best_score?: number | string | null;
  presentation_score?: number | string | null;
  cached_scores?: BackendCachedScore[];
};

type BackendExploreData = {
  cities?: BackendCity[];
  next_cursor?: string | null;
  service_filter?: string | null;
  growth_available?: boolean;
};

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

function getBaseUrl() {
  if (process.env.NEXT_PUBLIC_APP_FRONTEND_URL) {
    return process.env.NEXT_PUBLIC_APP_FRONTEND_URL;
  }
  if (process.env.NEXT_PUBLIC_APP_URL) return process.env.NEXT_PUBLIC_APP_URL;
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  return "http://localhost:3002";
}

function appendIfPresent(
  searchParams: URLSearchParams,
  key: string,
  value: string | number | boolean | undefined,
) {
  if (value === undefined || value === "") return;
  searchParams.append(key, String(value));
}

export function toExploreSearchParams(params: ExploreQueryParams = {}) {
  const searchParams = new URLSearchParams();
  appendIfPresent(searchParams, "service", params.service);

  const states = params.states ?? params.state;
  if (Array.isArray(states)) {
    for (const state of states) appendIfPresent(searchParams, "state", state);
  } else {
    appendIfPresent(searchParams, "state", states);
  }

  appendIfPresent(searchParams, "limit", params.limit);
  appendIfPresent(searchParams, "cursor", params.cursor);
  appendIfPresent(searchParams, "sort", backendSort(params.sort));
  appendIfPresent(searchParams, "direction", params.direction);
  appendIfPresent(
    searchParams,
    "population_min",
    params.population_min ?? params.min_population,
  );
  appendIfPresent(
    searchParams,
    "population_max",
    params.population_max ?? params.max_population,
  );
  appendIfPresent(searchParams, "income_min", params.income_min ?? params.min_income);
  appendIfPresent(searchParams, "income_max", params.income_max);
  appendIfPresent(searchParams, "growing_only", params.growing_only);
  return searchParams;
}

export function fromSearchParams(params: SearchParamRecord): ExploreQueryParams {
  const first = (value: string | string[] | undefined) =>
    Array.isArray(value) ? value[0] : value;
  const numberFrom = (value: string | string[] | undefined) => {
    const raw = first(value);
    if (raw === undefined || raw === "") return undefined;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : undefined;
  };

  const stateValue = params.state;
  const states = Array.isArray(stateValue)
    ? stateValue.filter(Boolean)
    : stateValue
      ? [stateValue]
      : undefined;

  return {
    service: first(params.service),
    states,
    limit: numberFrom(params.limit),
    cursor: first(params.cursor),
    sort: first(params.sort),
    direction: first(params.direction),
    population_min: numberFrom(params.population_min) ?? numberFrom(params.min_population),
    population_max: numberFrom(params.population_max) ?? numberFrom(params.max_population),
    income_min: numberFrom(params.income_min) ?? numberFrom(params.min_income),
    income_max: numberFrom(params.income_max),
    growing_only:
      first(params.growing_only) === undefined
        ? undefined
        : first(params.growing_only) === "true",
  };
}

function backendSort(sort: string | undefined) {
  if (sort === "best_opportunity") return "presentation_score";
  return sort;
}

function asNumber(value: number | string | null | undefined): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function scoreSystem(value: string | null | undefined): ExploreScoreSystem {
  if (value === "v2" || value === "legacy" || value === "none") return value;
  return "none";
}

function archetypeLabel(id: ArchetypeId): string {
  return ARCHETYPES.find((a) => a.id === id)?.short ?? "Mixed";
}

function archetypeFromScore(score: BackendCachedScore): ArchetypeId {
  const raw = score.archetype_id?.trim() || score.serp_archetype?.trim();
  if (raw) {
    const mapped = BACKEND_ARCHETYPE_MAP[raw.toUpperCase()];
    if (mapped) return mapped;
    if (ARCHETYPES.some((a) => a.id === raw)) return raw as ArchetypeId;
  }
  return deriveArchetype({
    opportunity_score:
      asNumber(score.opportunity_score) ?? asNumber(score.presentation_score),
  });
}

function normalizeCachedScore(score: BackendCachedScore): ExploreCachedScore {
  const presentationScore = asNumber(score.presentation_score);
  const opportunityScore = asNumber(score.opportunity_score) ?? presentationScore ?? 0;
  const service =
    score.service ??
    score.niche_keyword ??
    score.niche_normalized ??
    "Unknown service";
  const archetype_id = archetypeFromScore(score);
  const latestScoredAt = score.latest_scored_at ?? score.last_scored_at ?? "";

  return {
    ...score,
    report_id: score.report_id ?? "",
    service,
    niche_normalized: score.niche_normalized ?? null,
    niche_keyword: score.niche_keyword ?? null,
    opportunity_score: opportunityScore,
    score_system: scoreSystem(score.score_system),
    presentation_score: presentationScore,
    latest_scored_at: score.latest_scored_at ?? null,
    stale: score.stale ?? score.is_stale ?? null,
    last_refreshed_at: score.last_refreshed_at ?? (latestScoredAt || undefined),
    refresh_target_id: score.refresh_target_id,
    next_refresh_at: score.next_refresh_at,
    business_density_per_1k: asNumber(score.business_density_per_1k),
    establishment_growth_yoy: asNumber(score.establishment_growth_yoy),
    growth_available: score.growth_available ?? false,
    archetype_id,
    archetype_label: score.archetype_label ?? archetypeLabel(archetype_id),
    last_scored_at: latestScoredAt,
    is_stale: score.is_stale ?? score.stale ?? undefined,
  };
}

function averageOpportunityScore(scores: ExploreCachedScore[]) {
  if (scores.length === 0) return null;
  const total = scores.reduce((sum, score) => sum + score.opportunity_score, 0);
  return Math.round(total / scores.length);
}

function normalizeCity(city: BackendCity): ExploreCitySummary {
  const cachedScores = (city.cached_scores ?? []).map(normalizeCachedScore);
  const bestScore = asNumber(city.best_score);
  const presentationScore = asNumber(city.presentation_score);
  const bestOpportunityScore =
    asNumber(city.best_opportunity_score) ?? bestScore ?? presentationScore;

  return {
    cbsa_code: city.cbsa_code ?? "",
    cbsa_name: city.cbsa_name ?? "",
    state: city.state ?? "",
    population: asNumber(city.population),
    population_class: city.population_class ?? null,
    median_household_income_usd: asNumber(city.median_household_income_usd),
    owner_occupancy_rate: asNumber(city.owner_occupancy_rate),
    median_age_years: asNumber(city.median_age_years),
    business_density_per_1k: asNumber(city.business_density_per_1k),
    establishment_growth_yoy: asNumber(city.establishment_growth_yoy),
    growth_available: city.growth_available ?? false,
    score_system: scoreSystem(city.score_system),
    best_score: bestScore,
    presentation_score: presentationScore,
    representative_service: city.representative_service ?? null,
    metric_service: city.metric_service ?? null,
    last_scored_at: city.last_scored_at ?? city.latest_scored_at ?? null,
    latest_scored_at: city.latest_scored_at ?? null,
    stale: city.stale ?? null,
    service_filter: city.service_filter ?? null,
    cached_services_count: city.cached_services_count ?? cachedScores.length,
    best_opportunity_score: bestOpportunityScore,
    average_opportunity_score:
      asNumber(city.average_opportunity_score) ?? averageOpportunityScore(cachedScores),
    cached_scores: cachedScores,
  };
}

function normalizeExploreData(data: BackendExploreData): ExploreData {
  return {
    cities: (data.cities ?? []).map(normalizeCity),
    next_cursor: data.next_cursor ?? null,
    service_filter: data.service_filter ?? null,
    growth_available: data.growth_available,
  };
}

export async function loadExploreData(
  params: ExploreQueryParams = {},
): Promise<ExploreData> {
  const query = toExploreSearchParams(params);
  const queryString = query.toString();
  const url = `${getBaseUrl()}/api/explore/cities${queryString ? `?${queryString}` : ""}`;
  const response = await fetch(url, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`loadExploreData explore cities: HTTP ${response.status}`);
  }

  return normalizeExploreData((await response.json()) as BackendExploreData);
}
