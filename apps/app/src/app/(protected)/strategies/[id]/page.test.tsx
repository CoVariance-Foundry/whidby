// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import type { AnchorHTMLAttributes } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { StrategyCatalogEntry } from "@/lib/strategies/types";
import StrategyPage from "./page";

const mocks = vi.hoisted(() => ({
  loadDashboard: vi.fn(),
  loadStrategy: vi.fn(),
  notFound: vi.fn(() => {
    throw new Error("NEXT_NOT_FOUND");
  }),
  strategyClientProps: null as {
    strategy: StrategyCatalogEntry;
    lockedReason?: string | null;
    initialInputs?: Record<string, string>;
  } | null,
}));

vi.mock("@/lib/home/load-dashboard", () => ({
  loadDashboard: mocks.loadDashboard,
}));

vi.mock("@/lib/strategies/catalog", () => ({
  loadStrategy: mocks.loadStrategy,
}));

vi.mock("next/navigation", () => ({
  notFound: mocks.notFound,
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

vi.mock("./StrategyPageClient", () => ({
  default: (props: {
    strategy: StrategyCatalogEntry;
    lockedReason?: string | null;
    initialInputs?: Record<string, string>;
  }) => {
    mocks.strategyClientProps = props;
    return <div data-testid="strategy-page-client">{props.strategy.name}</div>;
  },
}));

const strategy: StrategyCatalogEntry = {
  strategy_id: "gbp_blitz",
  name: "GBP Blitz",
  description: "Local-pack momentum.",
  status: "launch",
  input_shape: "city_service",
  unlock_requirement: {
    requirement_id: "scan_completed",
    label: "Scan completed",
    description: "Complete a scan before starting GBP Blitz.",
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.strategyClientProps = null;
  mocks.loadStrategy.mockResolvedValue(strategy);
  mocks.loadDashboard.mockResolvedValue({
    onboarding: {
      has_completed_scan: true,
      has_ranked_site_declaration: true,
    },
  });
});

afterEach(cleanup);

describe("StrategyPage", () => {
  it("passes report query context into the strategy client initial inputs", async () => {
    const ui = await StrategyPage({
      params: Promise.resolve({ id: "gbp_blitz" }),
      searchParams: Promise.resolve({
        city: "Phoenix-Mesa-Chandler, AZ",
        service: "plumber",
        primary_keyword: "phoenix emergency plumber",
        reference_city_id: "38060",
        from_report: "1",
      }),
    });

    render(ui);

    expect(screen.getByTestId("strategy-page-client")).toHaveTextContent("GBP Blitz");
    expect(mocks.strategyClientProps?.initialInputs).toEqual({
      city: "Phoenix-Mesa-Chandler, AZ",
      service: "plumber",
      primary_keyword: "phoenix emergency plumber",
      reference_city_id: "38060",
    });
  });
});
