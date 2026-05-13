import type { ArchetypeId } from "@/lib/archetypes";

export interface ExploreCachedScore {
  report_id: string;
  service: string;
  opportunity_score: number;
  archetype_id: ArchetypeId;
  archetype_label: string;
  last_scored_at: string;
  confidence_score?: number;
  ai_resilience_score?: number;
  ai_exposure?: string;
  difficulty_tier?: string;
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
  cached_services_count: number;
  best_opportunity_score: number | null;
  average_opportunity_score: number | null;
  cached_scores: ExploreCachedScore[];
}

export interface ExploreData {
  cities: ExploreCitySummary[];
}
