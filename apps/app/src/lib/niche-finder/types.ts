export interface NicheQueryInput {
  city: string;
  service: string;
}

export interface NormalizedNicheQuery {
  cityInput: string;
  serviceInput: string;
  normalizedCity: string;
  normalizedService: string;
  queryKey: string;
}

export interface ScoreResult {
  opportunityScore: number;
  classificationLabel: "High" | "Medium" | "Low";
}

export type StandardResponseStatus =
  | "success"
  | "validation_error"
  | "unavailable";

export interface StandardSurfaceResponse {
  query: NicheQueryInput;
  scoreResult: ScoreResult;
  status: StandardResponseStatus;
  message?: string;
}
