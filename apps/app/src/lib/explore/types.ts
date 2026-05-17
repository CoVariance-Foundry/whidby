import type { ArchetypeId } from "@/lib/archetypes";

export type ExploreScoreSystem = "v2" | "legacy" | "none";

export interface ExploreCachedScore {
  report_id: string;
  service: string;
  opportunity_score: number;
  niche_normalized?: string | null;
  niche_keyword?: string | null;
  score_system?: ExploreScoreSystem;
  presentation_score?: number | null;
  latest_scored_at?: string | null;
  stale?: boolean | null;
  business_density_per_1k?: number | null;
  establishment_growth_yoy?: number | null;
  growth_available?: boolean;
  archetype_id: ArchetypeId;
  archetype_label: string;
  last_scored_at: string;
  confidence_score?: number;
  ai_resilience_score?: number;
  ai_exposure?: string;
  difficulty_tier?: string;
  refresh_target_id?: string;
  last_refreshed_at?: string;
  next_refresh_at?: string;
  stale_after_days?: number;
  is_stale?: boolean;
  opportunity_delta?: number | null;
}

export interface ExploreCitySummary {
  cbsa_code: string;
  cbsa_name: string;
  state: string;
  population: number | null;
  population_class: string | null;
  median_household_income_usd: number | null;
  owner_occupancy_rate: number | null;
  median_age_years: number | null;
  business_density_per_1k: number | null;
  establishment_growth_yoy: number | null;
  growth_available: boolean;
  score_system: ExploreScoreSystem;
  best_score: number | null;
  presentation_score: number | null;
  representative_service?: string | null;
  metric_service?: string | null;
  last_scored_at?: string | null;
  latest_scored_at?: string | null;
  stale?: boolean | null;
  service_filter?: string | null;
  cached_services_count: number;
  best_opportunity_score: number | null;
  average_opportunity_score: number | null;
  cached_scores: ExploreCachedScore[];
}

export interface ExploreData {
  cities: ExploreCitySummary[];
  next_cursor?: string | null;
  service_filter?: string | null;
  growth_available?: boolean;
}
