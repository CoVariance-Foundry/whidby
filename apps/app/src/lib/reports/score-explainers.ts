import { scoreToneForValue } from "@/lib/design-tokens";

export type ScoreKey =
  | "demand"
  | "organic_competition"
  | "local_competition"
  | "monetization"
  | "ai_resilience"
  | "opportunity";

export interface ScoreBand {
  label: string;
  range: string;
  color: string;
  bg: string;
}

export interface ScoreExplainer {
  title: string;
  definition: string;
  howToRead: string;
  bands: [ScoreBand, ScoreBand, ScoreBand, ScoreBand];
}

const HIGH = scoreToneForValue(80);
const GOOD = scoreToneForValue(60);
const WARNING = scoreToneForValue(40);
const DANGER = scoreToneForValue(39);

const SHARED_SCORE_GUIDANCE: [ScoreBand, ScoreBand, ScoreBand, ScoreBand] = [
  { label: "Danger", range: "0-39", color: DANGER.text, bg: DANGER.background },
  { label: "Warning", range: "40-59", color: WARNING.text, bg: WARNING.background },
  { label: "Good", range: "60-79", color: GOOD.text, bg: GOOD.background },
  { label: "High", range: "80-100", color: HIGH.text, bg: HIGH.background },
];

export const SCORE_EXPLAINERS: Record<ScoreKey, ScoreExplainer> = {
  demand: {
    title: "Demand",
    definition:
      "How much search volume exists for this niche in this metro, weighted by keyword value and buyer intent.",
    howToRead: "Higher score = more people actively searching for this service.",
    bands: SHARED_SCORE_GUIDANCE,
  },

  organic_competition: {
    title: "Organic Competition",
    definition:
      "How easy it is to rank in traditional Google search results, based on competitor domain authority, technical quality, and keyword targeting.",
    howToRead:
      "Higher score = weaker competition. A high score means incumbents are beatable with a well-built site.",
    bands: SHARED_SCORE_GUIDANCE,
  },

  local_competition: {
    title: "Local Competition",
    definition:
      "How easy it is to rank in the Google Local Pack and Maps, based on review counts, review velocity, and Google Business Profile quality of incumbents.",
    howToRead:
      "Higher score = weaker local competition. A high score means existing businesses have few reviews and under-optimized profiles.",
    bands: SHARED_SCORE_GUIDANCE,
  },

  monetization: {
    title: "Monetization",
    definition:
      "How likely you are to earn revenue if you rank, based on cost-per-click, local business density, ad spending, and lead-buying activity in the area.",
    howToRead:
      "Higher score = stronger revenue potential. Businesses here are already spending money on leads.",
    bands: SHARED_SCORE_GUIDANCE,
  },

  ai_resilience: {
    title: "AI Resilience",
    definition:
      "How protected this niche is from AI-driven traffic loss. Local, hands-on services are naturally shielded because AI can't replace a plumber or a roofer.",
    howToRead:
      "Higher score = more resilient. A high score means AI Overviews rarely appear and the service requires in-person fulfillment.",
    bands: SHARED_SCORE_GUIDANCE,
  },

  opportunity: {
    title: "Opportunity",
    definition:
      "The overall score combining demand, competition, monetization, and AI resilience into a single ranking signal. Weighted by your selected strategy profile.",
    howToRead:
      "Higher score = better overall opportunity. Scores below 40 indicate a critical weakness in at least one dimension.",
    bands: SHARED_SCORE_GUIDANCE,
  },
};
