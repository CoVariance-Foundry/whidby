import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fromSearchParams,
  loadExploreData,
  toExploreSearchParams,
} from "./load-explore-data";

const originalFetch = global.fetch;
const originalFrontendUrl = process.env.NEXT_PUBLIC_APP_FRONTEND_URL;
const originalLegacyAppUrl = process.env.NEXT_PUBLIC_APP_URL;
const originalVercelUrl = process.env.VERCEL_URL;

afterEach(() => {
  global.fetch = originalFetch;
  if (originalFrontendUrl === undefined) {
    delete process.env.NEXT_PUBLIC_APP_FRONTEND_URL;
  } else {
    process.env.NEXT_PUBLIC_APP_FRONTEND_URL = originalFrontendUrl;
  }
  if (originalLegacyAppUrl === undefined) {
    delete process.env.NEXT_PUBLIC_APP_URL;
  } else {
    process.env.NEXT_PUBLIC_APP_URL = originalLegacyAppUrl;
  }
  if (originalVercelUrl === undefined) {
    delete process.env.VERCEL_URL;
  } else {
    process.env.VERCEL_URL = originalVercelUrl;
  }
  vi.restoreAllMocks();
});

describe("toExploreSearchParams", () => {
  it("preserves repeated state filters", () => {
    expect(
      toExploreSearchParams({
        service: "roofing",
        states: ["AZ", "CO"],
        limit: 25,
        population_min: 50_000,
        population_max: 500_000,
        income_min: 60_000,
        income_max: 140_000,
        growing_only: true,
        sort: "best_opportunity",
        direction: "asc",
      }).toString(),
    ).toBe(
      "service=roofing&state=AZ&state=CO&limit=25&sort=presentation_score&direction=asc&population_min=50000&population_max=500000&income_min=60000&income_max=140000&growing_only=true",
    );
  });
});

describe("fromSearchParams", () => {
  it("normalizes Next search params into loader params", () => {
    expect(
      fromSearchParams({
        service: "roofing",
        state: ["AZ", "CO"],
        limit: "25",
        population_min: "50000",
        income_max: "140000",
        growing_only: "1",
        direction: "asc",
      }),
    ).toMatchObject({
      service: "roofing",
      states: ["AZ", "CO"],
      limit: 25,
      population_min: 50000,
      income_max: 140000,
      growing_only: true,
      direction: "asc",
    });
  });
});

describe("loadExploreData", () => {
  it("fetches the explore cities proxy with no-store caching", async () => {
    process.env.NEXT_PUBLIC_APP_FRONTEND_URL = "https://app.example.test";
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ cities: [] }), { status: 200 }),
    );
    global.fetch = fetchMock;

    await loadExploreData({ service: "roofing", states: ["AZ", "CO"], limit: 25 });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://app.example.test/api/explore/cities?service=roofing&state=AZ&state=CO&limit=25",
      { cache: "no-store" },
    );
  });

  it("defaults server-side fetches to the consumer app local port", async () => {
    delete process.env.NEXT_PUBLIC_APP_FRONTEND_URL;
    delete process.env.NEXT_PUBLIC_APP_URL;
    delete process.env.VERCEL_URL;
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ cities: [] }), { status: 200 }),
    );
    global.fetch = fetchMock;

    await loadExploreData();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:3002/api/explore/cities",
      { cache: "no-store" },
    );
  });

  it("maps backend rows to compatibility aliases for existing components", async () => {
    process.env.NEXT_PUBLIC_APP_FRONTEND_URL = "https://app.example.test";
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          next_cursor: "cursor-2",
          service_filter: "roofing",
          growth_available: true,
          cities: [
            {
              cbsa_code: "38060",
              cbsa_name: "Phoenix-Mesa-Chandler, AZ",
              state: "AZ",
              population: "5089000",
              population_class: "metro_1m_5m",
              median_household_income_usd: "82000",
              owner_occupancy_rate: "0.62",
              median_age_years: "37.1",
              business_density_per_1k: "2.4",
              establishment_growth_yoy: "0.031",
              growth_available: true,
              score_system: "v2",
              best_score: "91",
              presentation_score: "88",
              metric_service: "roofing",
              latest_scored_at: "2026-05-17T12:00:00Z",
              stale: false,
              cached_scores: [
                {
                  report_id: "report-1",
                  niche_normalized: "roofing",
                  niche_keyword: "Roofing",
                  score_system: "v2",
                  presentation_score: "88",
                  opportunity_score: null,
                  latest_scored_at: "2026-05-17T12:00:00Z",
                  refresh_target_id: "target-1",
                  next_refresh_at: "2026-06-17T12:00:00Z",
                  stale: false,
                  business_density_per_1k: "2.4",
                  establishment_growth_yoy: "0.031",
                  growth_available: true,
                },
              ],
            },
          ],
        }),
        { status: 200 },
      ),
    );

    const data = await loadExploreData({ service: "roofing" });

    expect(data).toMatchObject({
      next_cursor: "cursor-2",
      service_filter: "roofing",
      growth_available: true,
    });
    expect(data.cities[0]).toMatchObject({
      cbsa_code: "38060",
      population: 5089000,
      business_density_per_1k: 2.4,
      establishment_growth_yoy: 0.031,
      growth_available: true,
      score_system: "v2",
      best_score: 91,
      presentation_score: 88,
      best_opportunity_score: 91,
      average_opportunity_score: 88,
      metric_service: "roofing",
      latest_scored_at: "2026-05-17T12:00:00Z",
      stale: false,
    });
    expect(data.cities[0].cached_scores[0]).toMatchObject({
      service: "Roofing",
      opportunity_score: 88,
      presentation_score: 88,
      score_system: "v2",
      archetype_id: "PACK_VULN",
      archetype_label: "Pack, vulnerable",
      last_scored_at: "2026-05-17T12:00:00Z",
      last_refreshed_at: "2026-05-17T12:00:00Z",
      refresh_target_id: "target-1",
      next_refresh_at: "2026-06-17T12:00:00Z",
      stale: false,
    });
  });

  it("throws an HTTP-specific error for non-ok proxy responses", async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response("nope", { status: 502 }));

    await expect(loadExploreData()).rejects.toThrow(
      "loadExploreData explore cities: HTTP 502",
    );
  });
});
