import type { NicheQueryInput, ScoreResult } from "@/lib/niche-finder/types";

export interface EvidenceRecord {
  category: string;
  label: string;
  value: string | number | boolean;
  source: string;
  is_available: boolean;
}

export type ExplorationResponseStatus =
  | "success"
  | "partial_evidence"
  | "validation_error"
  | "unavailable";

export interface ExplorationSurfaceResponse {
  query: NicheQueryInput;
  score_result: ScoreResult;
  evidence: EvidenceRecord[];
  status: ExplorationResponseStatus;
  message?: string;
  report_id?: string;
}

export interface ExplorationAssistantRequest {
  session_id: string;
  query_context: NicheQueryInput;
  question: string;
}

export interface AssistantEvidenceReference {
  category: string;
  reference_label: string;
}

export type ExplorationAssistantStatus = "success" | "partial" | "unsupported";

export interface ExplorationAssistantResponse {
  response_id: string;
  session_id: string;
  query_context: NicheQueryInput;
  answer: string;
  evidence_references: AssistantEvidenceReference[];
  status: ExplorationAssistantStatus;
}
