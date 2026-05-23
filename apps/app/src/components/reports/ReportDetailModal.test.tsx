// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ReportDetailModal from "./ReportDetailModal";
import type { FullReportData } from "@/lib/niche-finder/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(() => ({
    rpc: vi.fn(),
  })),
}));

const report: FullReportData = {
  id: "rpt_123",
  created_at: "2026-05-22T12:00:00Z",
  spec_version: "1.0",
  niche_keyword: "plumber",
  geo_scope: "metro",
  geo_target: "Phoenix, AZ",
  report_depth: "standard",
  strategy_profile: "easy_win",
  resolved_weights: null,
  keyword_expansion: {
    expanded_keywords: [
      {
        keyword: "emergency plumber near me",
        tier: 1,
        intent: "transactional",
        search_volume: 1200,
      },
    ],
  },
  metros: [
    {
      cbsa_code: "38060",
      cbsa_name: "Phoenix-Mesa-Chandler, AZ",
      population: 4968450,
      serp_archetype: "EASY_WIN",
      difficulty_tier: "MODERATE",
      ai_exposure: "AI_MINIMAL",
      scores: {
        demand: 72,
        organic_competition: 65,
        local_competition: 58,
        monetization: 80,
        ai_resilience: 85,
        opportunity: 74,
        confidence: { score: 90 },
      },
      signals: {
        demand: {
          total_search_volume: 4200,
          avg_cpc: 12.5,
        },
        organic_competition: {
          avg_top5_da: 32,
        },
        local_competition: {
          review_velocity_avg: 3.5,
        },
        monetization: {
          business_density: 45,
        },
        ai_resilience: {
          aio_trigger_rate: 0.05,
        },
      },
      guidance: {
        summary: "Strong local service opportunity.",
        action_items: ["Audit the top three operators."],
      },
    },
  ],
  meta: null,
};

afterEach(cleanup);

describe("ReportDetailModal", () => {
  it("renders expanded report breakdowns and omits keyword expansion", () => {
    render(<ReportDetailModal report={report} onClose={vi.fn()} onDelete={vi.fn()} />);

    expect(screen.getByRole("dialog", { name: /report: plumber/i })).toBeInTheDocument();
    expect(screen.getByText("Organic Competition")).toBeInTheDocument();
    expect(screen.getByText("Local Competition")).toBeInTheDocument();
    expect(screen.getAllByText("Demand").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Monetization").length).toBeGreaterThan(0);
    expect(screen.getAllByText("AI Resilience").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /export json/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete report/i })).toBeInTheDocument();
    expect(screen.queryByText(/keyword expansion/i)).not.toBeInTheDocument();
    expect(screen.queryByText("emergency plumber near me")).not.toBeInTheDocument();
  });
});
