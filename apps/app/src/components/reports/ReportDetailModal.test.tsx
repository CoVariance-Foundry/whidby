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
    expect(screen.getAllByText("Organic ease").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Local ease").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Demand").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Monetization").length).toBeGreaterThan(0);
    expect(screen.getAllByText("AI Resilience").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /what is archetype/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /what is keyword difficulty \/ kd/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /export json/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete report/i })).toBeInTheDocument();
    expect(screen.queryByText(/keyword expansion/i)).not.toBeInTheDocument();
    expect(screen.queryByText("emergency plumber near me")).not.toBeInTheDocument();
  });

  it("links the top market to Competitor Intel with report context", () => {
    render(<ReportDetailModal report={report} onClose={vi.fn()} onDelete={vi.fn()} />);

    expect(screen.getByRole("link", { name: /open full report page/i })).toHaveAttribute(
      "href",
      "/reports/rpt_123",
    );

    const link = screen.getByRole("link", { name: /run competitor intel/i });
    const href = link.getAttribute("href");
    expect(href).toBeTruthy();

    const url = new URL(href ?? "", "http://localhost");
    expect(url.pathname).toBe("/competitor-intel");
    expect(url.searchParams.get("report_id")).toBe("rpt_123");
    expect(url.searchParams.get("city")).toBe("Phoenix-Mesa-Chandler, AZ");
    expect(url.searchParams.get("service")).toBe("plumber");
    expect(url.searchParams.get("cbsa_code")).toBe("38060");
  });

  it("renders WHI-163 next steps with locked ranked-site expansion by default", () => {
    render(<ReportDetailModal report={report} onClose={vi.fn()} onDelete={vi.fn()} />);

    const gbpBlitzLink = screen.getByRole("link", { name: /continue to gbp blitz/i });
    const href = gbpBlitzLink.getAttribute("href");
    expect(href).toBeTruthy();
    const url = new URL(href ?? "", "http://localhost");
    expect(url.pathname).toBe("/strategies/gbp_blitz");
    expect(url.searchParams.get("from_report")).toBe("1");
    expect(url.searchParams.get("report_id")).toBe("rpt_123");
    expect(url.searchParams.get("city")).toBe("Phoenix-Mesa-Chandler, AZ");
    expect(url.searchParams.get("service")).toBe("plumber");
    expect(url.searchParams.get("cbsa_code")).toBe("38060");
    expect(screen.getByText(/expand & conquer requires a ranked site/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /continue to expand & conquer/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/validate rank ease/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/find lookalike cities/i)).not.toBeInTheDocument();
  });

  it("unlocks Expand & Conquer next steps when ranked-site context is supplied", () => {
    render(
      <ReportDetailModal
        report={report}
        nextStepContext={{ has_completed_scan: true, has_ranked_site_declaration: true }}
        onClose={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    const expandConquerLink = screen.getByRole("link", { name: /continue to expand & conquer/i });
    const href = expandConquerLink.getAttribute("href");
    expect(href).toBeTruthy();
    const url = new URL(href ?? "", "http://localhost");
    expect(url.pathname).toBe("/strategies/expand_conquer");
    expect(url.searchParams.get("reference_city_id")).toBe("38060");
    expect(url.searchParams.get("service")).toBe("plumber");
    expect(screen.queryByText(/requires a ranked site/i)).not.toBeInTheDocument();
  });

  it("renders an AI Resilience flagged badge when report score is below the default threshold", () => {
    const flaggedReport: FullReportData = {
      ...report,
      metros: [
        {
          ...report.metros[0],
          scores: {
            ...report.metros[0].scores,
            ai_resilience: 32,
          },
        },
      ],
    };

    render(<ReportDetailModal report={flaggedReport} onClose={vi.fn()} onDelete={vi.fn()} />);

    expect(screen.getAllByText("AI resilience flagged")).toHaveLength(2);
    expect(screen.getAllByLabelText(/AI Resilience flagged: score 32 below threshold 40/i)).toHaveLength(2);
  });
});
