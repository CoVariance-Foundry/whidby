// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import type { AnchorHTMLAttributes } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ReportDetailPage from "./page";
import { notFound } from "next/navigation";

const mocks = vi.hoisted(() => ({
  headersGet: vi.fn(),
  loadCurrentProductUnlockState: vi.fn(),
  notFound: vi.fn(() => {
    throw new Error("NEXT_NOT_FOUND");
  }),
}));

vi.mock("next/headers", () => ({
  headers: vi.fn(async () => ({
    get: mocks.headersGet,
  })),
}));

vi.mock("next/navigation", () => ({
  notFound: mocks.notFound,
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
  }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
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

vi.mock("@/lib/onboarding/unlock-state", () => ({
  loadCurrentProductUnlockState: mocks.loadCurrentProductUnlockState,
}));

beforeEach(() => {
  delete process.env.WIDBY_APP_BASE_URL;
  delete process.env.NEXT_PUBLIC_APP_URL;
  delete process.env.NEXT_PUBLIC_SITE_URL;
  delete process.env.VERCEL_URL;
  mocks.headersGet.mockImplementation((name: string) => {
    const values: Record<string, string> = {
      host: "preview.whidby.test",
      cookie: "sb-access-token=abc",
    };
    return values[name] ?? null;
  });
  global.fetch = vi.fn();
  mocks.loadCurrentProductUnlockState.mockResolvedValue({
    has_completed_scan: true,
    has_ranked_site_declaration: false,
  });
  vi.clearAllMocks();
});

afterEach(cleanup);

describe("ReportDetailPage", () => {
  it("does not fetch a relative report URL for non-local request hosts", async () => {
    await expect(
      ReportDetailPage({
        params: Promise.resolve({ reportId: "report-1" }),
      }),
    ).rejects.toThrow("NEXT_NOT_FOUND");

    expect(global.fetch).not.toHaveBeenCalled();
    expect(mocks.loadCurrentProductUnlockState).not.toHaveBeenCalled();
    expect(notFound).toHaveBeenCalledOnce();
  });

  it("renders the shared V1.1 report detail surface from existing report data", async () => {
    process.env.WIDBY_APP_BASE_URL = "https://app.thewidby.test";
    mocks.loadCurrentProductUnlockState.mockResolvedValue({
      has_completed_scan: true,
      has_ranked_site_declaration: true,
    });
    vi.mocked(global.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "success",
          report: {
            id: "report-1",
            created_at: "2026-05-22T12:00:00Z",
            spec_version: "1.1",
            niche_keyword: "plumber",
            geo_scope: "metro",
            geo_target: "Phoenix, AZ",
            report_depth: "standard",
            strategy_profile: "balanced",
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
                },
              },
            ],
            meta: {
              ai_resilience_modifier: {
                threshold: 90,
                hide_flagged: true,
              },
            },
          },
        }),
        { status: 200 },
      ),
    );

    const ui = await ReportDetailPage({
      params: Promise.resolve({ reportId: "report-1" }),
    });
    const { container } = render(ui);

    expect(global.fetch).toHaveBeenCalledWith(
      "https://app.thewidby.test/api/agent/reports/report-1",
      expect.objectContaining({ cache: "no-store" }),
    );
    expect(screen.getByRole("heading", { name: "plumber" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /score and verdict/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /next steps/i })).toBeInTheDocument();
    expect(mocks.loadCurrentProductUnlockState).toHaveBeenCalledOnce();
    expect(screen.getByRole("link", { name: /continue to expand & conquer/i })).toHaveAttribute(
      "href",
      expect.stringContaining("/strategies/expand_conquer?"),
    );
    expect(screen.getAllByText("Standard scoring").length).toBeGreaterThan(0);
    expect(container).not.toHaveTextContent(/balanced/i);
    expect(screen.getByText("AI threshold: 90")).toBeInTheDocument();
    expect(screen.getAllByLabelText(/AI Resilience flagged: score 85 below threshold 90/i)).toHaveLength(2);
  });
});
