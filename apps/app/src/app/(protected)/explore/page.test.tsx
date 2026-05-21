// @vitest-environment jsdom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ExploreData } from "@/lib/explore/types";
import ExplorePage, { dynamic } from "./page";
import { loadExploreData } from "@/lib/explore/load-explore-data";

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

vi.mock("@/components/explore/ExplorePageClient", () => ({
  default: ({ data }: { data: ExploreData }) => (
    <section data-testid="explore-client" data-city-count={data.cities.length} />
  ),
}));

vi.mock("@/lib/explore/load-explore-data", () => ({
  fromSearchParams: vi.fn((params: Record<string, string | string[] | undefined>) => ({
    service: params.service,
    states: params.state,
    limit: Number(params.limit),
  })),
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
      growth_available: false,
      score_system: "none",
      best_score: null,
      presentation_score: null,
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
  it("uses a dynamic backend-backed route shell", async () => {
    vi.mocked(loadExploreData).mockResolvedValue(fixtureData);

    render(
      await ExplorePage({
        searchParams: Promise.resolve({
          service: "roofing",
          state: ["AZ", "CO"],
          limit: "25",
        }),
      }),
    );

    expect(dynamic).toBe("force-dynamic");
    expect(loadExploreData).toHaveBeenCalledWith({
      service: "roofing",
      states: ["AZ", "CO"],
      limit: 25,
    });
    expect(screen.getByTestId("explore-client").getAttribute("data-city-count")).toBe("1");
  });
});
