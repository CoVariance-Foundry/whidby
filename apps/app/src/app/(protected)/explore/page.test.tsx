// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ExploreData } from "@/lib/explore/types";
import ExplorePage, { dynamic } from "./page";
import { loadExploreData } from "@/lib/explore/load-explore-data";
import { createClient } from "@/lib/supabase/server";

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

vi.mock("@/components/Sidebar", () => ({
  default: ({ active }: { active: string }) => (
    <nav data-testid="sidebar" data-active={active} />
  ),
}));

vi.mock("@/components/Topbar", () => ({
  default: ({
    crumbs,
    actions,
  }: {
    crumbs: string[];
    actions?: React.ReactNode;
  }) => (
    <header data-testid="topbar" data-crumbs={crumbs.join("/")}>
      {actions}
    </header>
  ),
}));

vi.mock("@/components/explore/ExplorePageClient", () => ({
  default: ({ data }: { data: ExploreData }) => (
    <section data-testid="explore-client" data-city-count={data.cities.length} />
  ),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(),
}));

vi.mock("@/lib/explore/load-explore-data", () => ({
  loadExploreData: vi.fn(),
}));

const fixtureData: ExploreData = {
  cities: [
    {
      cbsa_code: "11111",
      cbsa_name: "Austin-Round Rock-Georgetown, TX",
      state: "TX",
      population: 2300000,
      population_class: "metro_1m_5m",
      median_household_income_usd: 91000,
      owner_occupancy_rate: 0.58,
      median_age_years: 35.8,
      business_density_per_1k: null,
      establishment_growth_yoy: null,
      cached_services_count: 1,
      best_opportunity_score: 82,
      average_opportunity_score: 82,
      cached_scores: [],
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ExplorePage", () => {
  it("uses a dynamic Supabase-backed route shell", async () => {
    const supabase = { from: vi.fn() };
    vi.mocked(createClient).mockResolvedValue(supabase as never);
    vi.mocked(loadExploreData).mockResolvedValue(fixtureData);

    render(await ExplorePage());

    expect(dynamic).toBe("force-dynamic");
    expect(createClient).toHaveBeenCalledTimes(1);
    expect(loadExploreData).toHaveBeenCalledWith(supabase);
    expect(screen.getByTestId("sidebar").getAttribute("data-active")).toBe("explore");
    expect(screen.getByTestId("topbar").getAttribute("data-crumbs")).toBe("Explore");
    expect(screen.getByTestId("explore-client").getAttribute("data-city-count")).toBe("1");
    expect(screen.getByRole("link", { name: /new report/i }).getAttribute("href")).toBe(
      "/niche-finder",
    );
  });
});
