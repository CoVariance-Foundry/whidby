import type {
  ExplorationSurfaceResponse,
  EvidenceRecord,
} from "@/lib/niche-finder/exploration-types";
import type {
  NicheQueryInput,
  ScoreResult,
  StandardSurfaceResponse,
} from "@/lib/niche-finder/types";
import { normalizeQueryInput } from "@/lib/niche-finder/query-normalization";

function scoreHash(input: string): number {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash * 31 + input.charCodeAt(i)) % 100000;
  }
  return hash;
}

function classifyScore(score: number): ScoreResult["classification_label"] {
  if (score >= 75) return "High";
  if (score >= 50) return "Medium";
  return "Low";
}

export function buildScoreResult(input: NicheQueryInput): ScoreResult {
  const normalized = normalizeQueryInput(input);
  const raw = scoreHash(normalized.queryKey);
  const opportunityScore = 30 + (raw % 71);

  return {
    opportunity_score: opportunityScore,
    classification_label: classifyScore(opportunityScore),
  };
}

function buildEvidence(score: ScoreResult, input: NicheQueryInput): EvidenceRecord[] {
  const normalized = normalizeQueryInput(input);
  const demand = (score.opportunity_score + scoreHash(normalized.normalizedCity)) % 100;
  const competition =
    (scoreHash(normalized.normalizedService) + score.opportunity_score) % 100;
  const monetization = (demand + competition + 17) % 100;
  const resilience = (100 - competition + 23) % 100;

  return [
    {
      category: "demand",
      label: "Relative Market Demand",
      value: demand,
      source: "Derived exploration baseline",
      is_available: true,
    },
    {
      category: "competition",
      label: "Relative Competition Pressure",
      value: competition,
      source: "Derived exploration baseline",
      is_available: true,
    },
    {
      category: "monetization",
      label: "Commercial Intent Signal",
      value: monetization,
      source: "Derived exploration baseline",
      is_available: true,
    },
    {
      category: "ai_resilience",
      label: "AI Resilience Signal",
      value: resilience,
      source: "Derived exploration baseline",
      is_available: true,
    },
  ];
}

export function buildStandardResponse(query: NicheQueryInput): StandardSurfaceResponse {
  return {
    query,
    score_result: buildScoreResult(query),
    status: "success",
  };
}

export function buildExplorationResponse(query: NicheQueryInput): ExplorationSurfaceResponse {
  const score_result = buildScoreResult(query);
  const evidence = buildEvidence(score_result, query);

  return {
    query,
    score_result,
    evidence,
    status: evidence.length > 0 ? "success" : "partial_evidence",
  };
}
