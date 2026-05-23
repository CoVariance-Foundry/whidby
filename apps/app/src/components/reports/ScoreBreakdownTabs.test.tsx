// @vitest-environment jsdom
import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, it, expect } from "vitest";
import ScoreBreakdownTabs from "./ScoreBreakdownTabs";
import type { MetroScores } from "@/lib/niche-finder/types";

afterEach(cleanup);

const scores: MetroScores = {
  demand: 72,
  organic_competition: 65,
  local_competition: 58,
  monetization: 80,
  ai_resilience: 85,
  opportunity: 74,
};

const signals: Record<string, unknown> = {
  demand: {
    total_search_volume: 4200,
    effective_search_volume: 3500,
    head_term_volume: 2000,
    volume_breadth: 0.8,
    avg_cpc: 12.5,
    max_cpc: 25.0,
    cpc_volume_product: 43750,
    transactional_ratio: 0.65,
  },
  organic_competition: {
    avg_top5_da: 32,
    min_top5_da: 15,
    da_spread: 17,
    aggregator_count: 2,
    local_biz_count: 5,
    avg_lighthouse_performance: 45,
    schema_adoption_rate: 0.2,
    title_keyword_match_rate: 0.3,
  },
  local_competition: {
    local_pack_present: true,
    local_pack_position: 2,
    local_pack_review_count_avg: 35,
    local_pack_review_count_max: 120,
    local_pack_rating_avg: 4.2,
    review_velocity_avg: 3.5,
    gbp_completeness_avg: 0.6,
    gbp_photo_count_avg: 15,
    gbp_posting_activity: 0.3,
    citation_consistency: 0.7,
  },
  monetization: {
    avg_cpc: 12.5,
    business_density: 45,
    gbp_completeness_avg: 0.6,
    lsa_present: true,
    aggregator_presence: 2,
    ads_present: true,
  },
  ai_resilience: {
    aio_trigger_rate: 0.05,
    featured_snippet_rate: 0.1,
    transactional_keyword_ratio: 0.65,
    local_fulfillment_required: 1,
    paa_density: 2.0,
  },
};

describe("ScoreBreakdownTabs", () => {
  it("renders the score breakdown as native expanded sections", () => {
    render(<ScoreBreakdownTabs signals={signals} scores={scores} />);

    expect(screen.getByRole("region", { name: /score breakdown/i })).toBeInTheDocument();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    expect(screen.queryByRole("tabpanel")).not.toBeInTheDocument();
  });

  it("shows competition, demand, monetization, and ai resilience on initial render", () => {
    render(<ScoreBreakdownTabs signals={signals} scores={scores} />);

    expect(screen.getByText("Organic Competition")).toBeInTheDocument();
    expect(screen.getByText("Local Competition")).toBeInTheDocument();
    expect(screen.getByText("Demand")).toBeInTheDocument();
    expect(screen.getByText("Monetization")).toBeInTheDocument();
    expect(screen.getByText("AI Resilience")).toBeInTheDocument();
  });

  it("renders representative signals without user interaction", () => {
    render(<ScoreBreakdownTabs signals={signals} scores={scores} />);

    expect(screen.getByText("Total search volume")).toBeInTheDocument();
    expect(screen.getByText("Business density")).toBeInTheDocument();
    expect(screen.getByText("AI Overview trigger rate")).toBeInTheDocument();
    expect(screen.getByText("Avg. DA (top 5)")).toBeInTheDocument();
    expect(screen.getByText("Review velocity")).toBeInTheDocument();
  });
});
