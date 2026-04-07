import type { NicheQueryInput, ScoreResult } from "@/lib/niche-finder/types";

export interface EvidenceRecord {
  category: string;
  label: string;
  value: string | number | boolean;
  source: string;
  isAvailable: boolean;
}

export type ExplorationResponseStatus =
  | "success"
  | "partial_evidence"
  | "validation_error"
  | "unavailable";

export interface ExplorationSurfaceResponse {
  query: NicheQueryInput;
  scoreResult: ScoreResult;
  evidence: EvidenceRecord[];
  status: ExplorationResponseStatus;
  message?: string;
}

export interface ExplorationAssistantRequest {
  sessionId: string;
  queryContext: NicheQueryInput;
  question: string;
}

export interface AssistantEvidenceReference {
  category: string;
  referenceLabel: string;
}

export type ExplorationAssistantStatus = "success" | "partial" | "unsupported";

export interface ExplorationAssistantResponse {
  responseId: string;
  sessionId: string;
  queryContext: NicheQueryInput;
  answer: string;
  evidenceReferences: AssistantEvidenceReference[];
  status: ExplorationAssistantStatus;
}
