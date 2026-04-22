// @vitest-environment jsdom
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
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
  it("renders four tab buttons", () => {
    render(<ScoreBreakdownTabs signals={signals} scores={scores} />);
    expect(screen.getByRole("tab", { name: /competition/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /demand/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /monetization/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /ai resilience/i })).toBeInTheDocument();
  });

  it("starts with no panel visible", () => {
    render(<ScoreBreakdownTabs signals={signals} scores={scores} />);
    expect(screen.queryByRole("tabpanel")).not.toBeInTheDocument();
  });

  it("clicking Competition tab shows organic and local panels", () => {
    render(<ScoreBreakdownTabs signals={signals} scores={scores} />);
    fireEvent.click(screen.getByRole("tab", { name: /competition/i }));
    expect(screen.getByRole("tabpanel")).toBeInTheDocument();
    expect(screen.getByText("Organic Competition")).toBeInTheDocument();
    expect(screen.getByText("Local Competition")).toBeInTheDocument();
  });

  it("clicking Demand tab shows demand signals", () => {
    render(<ScoreBreakdownTabs signals={signals} scores={scores} />);
    fireEvent.click(screen.getByRole("tab", { name: /demand/i }));
    expect(screen.getByText("Total search volume")).toBeInTheDocument();
    expect(screen.getByText("Avg. CPC")).toBeInTheDocument();
  });

  it("clicking Monetization tab shows monetization signals", () => {
    render(<ScoreBreakdownTabs signals={signals} scores={scores} />);
    fireEvent.click(screen.getByRole("tab", { name: /monetization/i }));
    expect(screen.getByText("Business density")).toBeInTheDocument();
    expect(screen.getByText("Local Services Ads")).toBeInTheDocument();
  });

  it("clicking AI Resilience tab shows ai signals", () => {
    render(<ScoreBreakdownTabs signals={signals} scores={scores} />);
    fireEvent.click(screen.getByRole("tab", { name: /ai resilience/i }));
    expect(screen.getByText("AI Overview trigger rate")).toBeInTheDocument();
    expect(screen.getByText("PAA density")).toBeInTheDocument();
  });

  it("clicking the active tab again collapses the panel", () => {
    render(<ScoreBreakdownTabs signals={signals} scores={scores} />);
    const tab = screen.getByRole("tab", { name: /demand/i });
    fireEvent.click(tab);
    expect(screen.getByRole("tabpanel")).toBeInTheDocument();
    fireEvent.click(tab);
    expect(screen.queryByRole("tabpanel")).not.toBeInTheDocument();
  });

  it("switching tabs changes panel content", () => {
    render(<ScoreBreakdownTabs signals={signals} scores={scores} />);
    fireEvent.click(screen.getByRole("tab", { name: /demand/i }));
    expect(screen.getByText("Total search volume")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /monetization/i }));
    expect(screen.queryByText("Total search volume")).not.toBeInTheDocument();
    expect(screen.getByText("Business density")).toBeInTheDocument();
  });
});
