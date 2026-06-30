// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StrategyResultSummary } from "./StrategyResultSummary";
import {
  createInlineStrategyResultSummary,
  createReportStrategyResultSummary,
} from "@/lib/strategy-result-summary";
import type { FullReportData } from "@/lib/niche-finder/types";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

afterEach(cleanup);

describe("StrategyResultSummary", () => {
  it("renders inline strategy result DTO with score, context, AI flag, and full-report CTA", () => {
    const summary = createInlineStrategyResultSummary({
      id: "boise-plumbing",
      city: "Boise",
      service: "Plumbing",
      rank: 1,
      score: 86,
      confidenceScore: 72,
      aiResilienceScore: 32,
      evidence: ["Weak local pack"],
      warnings: ["AI overview present"],
      reportId: "report-1",
      sourceContext: {
        strategy_id: "keyword_hijack",
        segment: "launch",
        modifier_state: { threshold: 40, hide_flagged: true },
      },
    });

    render(<StrategyResultSummary summary={summary} aiResilienceThreshold={40} />);

    expect(screen.getByText("Plumbing in Boise")).toBeInTheDocument();
    expect(screen.getByText("Rank #1")).toBeInTheDocument();
    expect(screen.getByText("keyword_hijack")).toBeInTheDocument();
    expect(screen.getByText("AI threshold: 40")).toBeInTheDocument();
    expect(screen.getByText("Hide flagged")).toBeInTheDocument();
    expect(screen.getByText("Weak local pack")).toBeInTheDocument();
    expect(screen.getByText("AI overview present")).toBeInTheDocument();
    expect(screen.getByText("AI resilience flagged")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Strategy score: 86 out of 100, high" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open full report/i })).toHaveAttribute(
      "href",
      "/reports?open=report-1",
    );
  });

  it("builds report summary DTOs with durable report context", () => {
    const report: FullReportData = {
      id: "report-2",
      created_at: "2026-05-22T12:00:00Z",
      spec_version: "1.0",
      niche_keyword: "plumber",
      geo_scope: "metro",
      geo_target: "Phoenix, AZ",
      report_depth: "standard",
      strategy_profile: "easy_win",
      resolved_weights: null,
      keyword_expansion: null,
      metros: [
        {
          cbsa_code: "38060",
          cbsa_name: "Phoenix-Mesa-Chandler, AZ",
          scores: {
            demand: 72,
            organic_competition: 65,
            local_competition: 58,
            monetization: 80,
            ai_resilience: 85,
            opportunity: 74,
            confidence: { score: 90, flags: ["sample_size_warning"] },
          },
          guidance: { summary: "Strong local service opportunity." },
          difficulty_tier: "MODERATE",
        },
      ],
      meta: null,
    };

    const summary = createReportStrategyResultSummary({
      report,
      metro: report.metros[0],
    });

    expect(summary).toMatchObject({
      id: "report-2:38060",
      title: "plumber in Phoenix-Mesa-Chandler, AZ",
      score: 74,
      score_label: "Opportunity score",
      verdict: "MODERATE",
      confidence_score: 90,
      ai_resilience_score: 85,
      evidence: ["Strong local service opportunity."],
      warnings: ["sample_size_warning"],
      report_href: "/reports/report-2",
      source_context: {
        strategy_id: "easy_win",
        city: "Phoenix-Mesa-Chandler, AZ",
        service: "plumber",
        segment: "standard",
      },
    });
  });
});
