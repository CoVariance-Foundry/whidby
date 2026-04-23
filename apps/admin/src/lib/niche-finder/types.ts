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
}
