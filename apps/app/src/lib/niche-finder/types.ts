// Mirror of apps/admin/src/lib/niche-finder/types.ts. Keep in sync until lifted to packages/.

export interface NicheQueryInput {
  city: string;
  service: string;
  /** Two-letter state abbreviation resolved via CityAutocomplete (optional). */
  state?: string;
  /** Canonical Mapbox place identifier selected from autocomplete (optional). */
  place_id?: string;
  /** DataForSEO location code bridged from selected place (optional). */
  dataforseo_location_code?: number;
}

export interface NormalizedNicheQuery {
  cityInput: string;
  serviceInput: string;
  normalizedCity: string;
  normalizedService: string;
  queryKey: string;
}

export interface ScoreResult {
  opportunity_score: number;
  classification_label: "High" | "Medium" | "Low";
}

export type StandardResponseStatus =
  | "success"
  | "validation_error"
  | "unavailable";

export interface StandardSurfaceResponse {
  query: NicheQueryInput;
  score_result: ScoreResult;
  status: StandardResponseStatus;
  message?: string;
  report_id?: string;
  entity_id?: string | null;
  snapshot_id?: string | null;
  persist_warning?: string | null;
}

export interface MetroScores {
  demand: number;
  organic_competition: number;
  local_competition: number;
  monetization: number;
  ai_resilience: number;
  opportunity: number;
  confidence?: { score: number; flags?: string[] };
}

export interface MetroGuidance {
  summary?: string;
  action_items?: string[];
  [key: string]: unknown;
}

export interface ReportMetro {
  cbsa_code: string;
  cbsa_name: string;
  population?: number;
  scores: MetroScores;
  serp_archetype?: string;
  ai_exposure?: string;
  difficulty_tier?: string;
  signals?: Record<string, unknown>;
  guidance?: MetroGuidance;
}

export interface KeywordExpansionItem {
  keyword: string;
  tier?: number;
  intent?: string;
  source?: string;
  aio_risk?: string;
  search_volume?: number;
  cpc?: number;
}

export interface FullReportData {
  id: string;
  created_at: string;
  spec_version: string;
  niche_keyword: string;
  geo_scope: string;
  geo_target: string;
  report_depth: string;
  strategy_profile: string;
  resolved_weights: Record<string, number> | null;
  keyword_expansion: { expanded_keywords?: KeywordExpansionItem[] } | null;
  metros: ReportMetro[];
  meta: Record<string, unknown> | null;
}
