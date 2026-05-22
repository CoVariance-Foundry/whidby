// @vitest-environment jsdom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CompetitorIntelClient from "./CompetitorIntelClient";
import type {
  CompetitorIntelAccount,
  CompetitorIntelTarget,
  CompetitorIntelViewState,
} from "@/lib/competitor-intel/types";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const paidAccount: CompetitorIntelAccount = {
  plan_key: "plus",
  plan_label: "Plus",
  monthly_report_limit: 10,
  fresh_reports_remaining: 6,
};

const freeAccount: CompetitorIntelAccount = {
  plan_key: "free",
  plan_label: "Free",
  monthly_report_limit: 0,
  fresh_reports_remaining: 0,
};

const target: CompetitorIntelTarget = {
  city: "Flagstaff",
  state: "AZ",
  service: "Plumbing",
  cbsa_code: "22380",
  place_id: "place.123",
  dataforseo_location_code: 1013401,
};

function renderClient({
  account = paidAccount,
  initialState,
  targetOverride,
}: {
  account?: CompetitorIntelAccount;
  initialState?: CompetitorIntelViewState;
  targetOverride?: Partial<CompetitorIntelTarget>;
} = {}) {
  return render(
    <CompetitorIntelClient
      account={account}
      target={{ ...target, ...targetOverride }}
      initialState={initialState}
    />,
  );
}

beforeEach(() => {
  global.fetch = vi.fn();
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CompetitorIntelClient", () => {
  it("does not render competitor details for free upgrade state", () => {
    renderClient({ account: freeAccount });

    expect(screen.getByRole("heading", { name: /competitor intel needs a paid plan/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view plans/i })).toHaveAttribute("href", "/settings");
    expect(screen.queryByRole("heading", { name: /organic competitors/i })).not.toBeInTheDocument();
    expect(screen.queryByText("flagstaffplumbers.com")).not.toBeInTheDocument();
  });

  it("shows the 2-scan cost and remaining scans for paid ready state", () => {
    renderClient({ initialState: { kind: "ready_to_run" } });

    expect(screen.getByText("2 scans")).toBeInTheDocument();
    expect(screen.getByText("6")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run competitor intel/i })).toBeEnabled();
  });

  it("requires confirmation before POSTing the run and propagates route params", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "running",
          run_id: "run-1",
          message: "Queued",
        }),
      ) as never,
    );
    renderClient({ initialState: { kind: "ready_to_run" } });

    fireEvent.click(screen.getByRole("button", { name: /run competitor intel/i }));

    expect(fetch).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog", { name: /confirm 2-scan run/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /confirm run/i }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/competitor-intel/runs",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...target,
            scan_cost: 2,
          }),
        }),
      );
    });
    expect(await screen.findByRole("heading", { name: /competitor intel is in progress/i })).toBeInTheDocument();
  });

  it("loads durable state for direct city and service links", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "aggregate_only",
          aggregate: {
            city: "Flagstaff",
            state: "AZ",
            service: "Plumbing",
            market_ledger: [{ label: "Market", value: "Flagstaff, AZ" }],
            summary_metrics: [{ label: "Avg top-5 DA", value: 21 }],
            coverage: [{ label: "Organic SERP competitors", status: "partial" }],
          },
        }),
      ) as never,
    );

    renderClient();

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/competitor-intel?city=Flagstaff&state=AZ&service=Plumbing&cbsa_code=22380&place_id=place.123&dataforseo_location_code=1013401",
      );
    });
    expect(await screen.findByText(/market-level evidence is available/i)).toBeInTheDocument();
  });

  it("renders aggregate-only evidence without dossier sections", () => {
    renderClient({
      initialState: {
        kind: "aggregate_only",
        aggregate: {
          city: "Flagstaff",
          state: "AZ",
          service: "Plumbing",
          market_ledger: [
            { label: "Market", value: "Flagstaff, AZ" },
            { label: "Service", value: "Plumbing" },
          ],
          summary_metrics: [
            { label: "Avg DA", value: 19 },
            { label: "Schema adoption", value: "0%" },
          ],
          coverage: [
            { label: "Organic SERP competitors", status: "partial", detail: "Aggregate top-5 only." },
            { label: "Local pack competitors", status: "missing", detail: "Maps rows pending." },
          ],
        },
      },
    });

    expect(screen.getByText(/market-level evidence is available/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /market ledger/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /coverage/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /organic competitors/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /win plan/i })).not.toBeInTheDocument();
  });

  it("renders a completed dossier without null clutter", () => {
    renderClient({
      initialState: {
        kind: "dossier",
        report: {
          report_id: "report-1",
          city: "Flagstaff",
          state: "AZ",
          service: "Plumbing",
          generated_at: "2026-05-22T00:00:00.000Z",
          market_ledger: [
            { label: "Market", value: "Flagstaff, AZ" },
            { label: "Report", value: null },
          ],
          summary_metrics: [{ label: "Avg DA", value: 19 }],
          organic_competitors: [
            {
              rank: 1,
              domain: "flagstaffplumbers.com",
              domain_authority: 22,
              schema_adoption: false,
              weaknesses: ["No schema markup"],
            },
          ],
          local_pack_competitors: [
            {
              rank: 1,
              name: "Flagstaff Plumbers",
              rating: 4.2,
              review_count: 27,
              weaknesses: ["Low review velocity"],
            },
          ],
          win_plan: [
            {
              title: "Ship LocalBusiness schema",
              play: "Add JSON-LD LocalBusiness and Service schema on every service page.",
              estimated_impact: "High",
              rationale: "No local competitor is using schema.",
            },
          ],
          coverage: [
            { label: "Organic SERP competitors", status: "available", detail: "1 ranked competitor" },
            { label: "GBP post history", status: "missing", detail: "Not returned by the run." },
          ],
        },
      },
    });

    expect(screen.getByRole("heading", { name: /organic competitors/i })).toBeInTheDocument();
    expect(screen.getByText("flagstaffplumbers.com")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /local-pack competitors/i })).toBeInTheDocument();
    expect(screen.getByText("Flagstaff Plumbers")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /win plan/i })).toBeInTheDocument();
    expect(screen.getByText("Ship LocalBusiness schema")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /coverage/i })).toBeInTheDocument();
    expect(screen.getByText("GBP post history")).toBeInTheDocument();
    expect(screen.queryByText(/^null$/i)).not.toBeInTheDocument();
  });
});
