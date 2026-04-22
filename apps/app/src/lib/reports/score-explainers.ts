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
  bands: [ScoreBand, ScoreBand, ScoreBand];
}

const GREEN = { color: "#0f7a57", bg: "#dfede6" };
const AMBER = { color: "#a05a00", bg: "#f6ebd4" };
const RED = { color: "#a3292d", bg: "#f3e1e1" };

export const SCORE_EXPLAINERS: Record<ScoreKey, ScoreExplainer> = {
  demand: {
    title: "Demand",
    definition:
      "How much search volume exists for this niche in this metro, weighted by keyword value and buyer intent.",
    howToRead: "Higher score = more people actively searching for this service.",
    bands: [
      { label: "Low", range: "0–49", ...RED },
      { label: "Medium", range: "50–74", ...AMBER },
      { label: "High", range: "75–100", ...GREEN },
    ],
  },

  organic_competition: {
    title: "Organic Competition",
    definition:
      "How easy it is to rank in traditional Google search results, based on competitor domain authority, technical quality, and keyword targeting.",
    howToRead:
      "Higher score = weaker competition. A high score means incumbents are beatable with a well-built site.",
    bands: [
      { label: "Hard", range: "0–49", ...RED },
      { label: "Moderate", range: "50–74", ...AMBER },
      { label: "Easy", range: "75–100", ...GREEN },
    ],
  },

  local_competition: {
    title: "Local Competition",
    definition:
      "How easy it is to rank in the Google Local Pack and Maps, based on review counts, review velocity, and Google Business Profile quality of incumbents.",
    howToRead:
      "Higher score = weaker local competition. A high score means existing businesses have few reviews and under-optimized profiles.",
    bands: [
      { label: "Hard", range: "0–49", ...RED },
      { label: "Moderate", range: "50–74", ...AMBER },
      { label: "Easy", range: "75–100", ...GREEN },
    ],
  },

  monetization: {
    title: "Monetization",
    definition:
      "How likely you are to earn revenue if you rank, based on cost-per-click, local business density, ad spending, and lead-buying activity in the area.",
    howToRead:
      "Higher score = stronger revenue potential. Businesses here are already spending money on leads.",
    bands: [
      { label: "Low", range: "0–49", ...RED },
      { label: "Medium", range: "50–74", ...AMBER },
      { label: "High", range: "75–100", ...GREEN },
    ],
  },

  ai_resilience: {
    title: "AI Resilience",
    definition:
      "How protected this niche is from AI-driven traffic loss. Local, hands-on services are naturally shielded because AI can't replace a plumber or a roofer.",
    howToRead:
      "Higher score = more resilient. A high score means AI Overviews rarely appear and the service requires in-person fulfillment.",
    bands: [
      { label: "Exposed", range: "0–49", ...RED },
      { label: "Moderate", range: "50–74", ...AMBER },
      { label: "Shielded", range: "75–100", ...GREEN },
    ],
  },

  opportunity: {
    title: "Opportunity",
    definition:
      "The overall score combining demand, competition, monetization, and AI resilience into a single ranking signal. Weighted by your selected strategy profile.",
    howToRead:
      "Higher score = better overall opportunity. Scores below 40 indicate a critical weakness in at least one dimension.",
    bands: [
      { label: "Low", range: "0–49", ...RED },
      { label: "Medium", range: "50–74", ...AMBER },
      { label: "High", range: "75–100", ...GREEN },
    ],
  },
};
