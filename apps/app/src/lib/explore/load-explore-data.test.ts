import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  headerGet: vi.fn(),
}));

vi.mock("next/headers", () => ({
  headers: vi.fn(async () => ({
    get: mocks.headerGet,
  })),
}));

import {
  fromSearchParams,
  toExploreSearchParams,
} from "./normalize-explore-data";
import { loadExploreData } from "./load-explore-data";

const originalFetch = global.fetch;
const originalNodeEnv = process.env.NODE_ENV;
const originalVercelEnv = process.env.VERCEL_ENV;
const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;

afterEach(() => {
  global.fetch = originalFetch;
  delete process.env.WIDBY_APP_BASE_URL;
  delete process.env.NEXT_PUBLIC_APP_URL;
  delete process.env.NEXT_PUBLIC_SITE_URL;
  delete process.env.VERCEL_URL;
  if (originalApiUrl === undefined) {
    delete process.env.NEXT_PUBLIC_API_URL;
  } else {
    process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
  }
  if (originalNodeEnv === undefined) {
    delete process.env.NODE_ENV;
  } else {
    process.env.NODE_ENV = originalNodeEnv;
  }
  if (originalVercelEnv === undefined) {
    delete process.env.VERCEL_ENV;
  } else {
    process.env.VERCEL_ENV = originalVercelEnv;
  }
  vi.unstubAllGlobals();
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
  it("fetches the FastAPI explore cities route directly on the server", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ cities: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    global.fetch = fetchMock;
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test/";

    await loadExploreData(
      { service: "roofing", states: ["AZ", "CO"], limit: 25 },
      { app_base_url: "https://app.example.test/" },
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/api/explore/cities?service=roofing&state=AZ&state=CO&limit=25",
      { cache: "no-store" },
    );
  });

  it("allows relative app route fetches in browser-safe contexts", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ cities: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    global.fetch = fetchMock;
    vi.stubGlobal("window", {});

    await loadExploreData();

    expect(fetchMock).toHaveBeenCalledWith("/api/explore/cities", {
      cache: "no-store",
    });
  });

  it("throws loudly when production server rendering is missing NEXT_PUBLIC_API_URL", async () => {
    process.env.NODE_ENV = "production";
    delete process.env.NEXT_PUBLIC_API_URL;
    global.fetch = vi.fn();

    await expect(
      loadExploreData({}, { app_base_url: "https://app.example.test" }),
    ).rejects.toThrow(
      "NEXT_PUBLIC_API_URL is required in deployed environments and must point to the API/Render service",
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("throws loudly when Vercel preview server rendering is missing NEXT_PUBLIC_API_URL", async () => {
    process.env.VERCEL_ENV = "preview";
    delete process.env.NEXT_PUBLIC_API_URL;
    global.fetch = vi.fn();

    await expect(
      loadExploreData({}, { app_base_url: "https://preview.example.test" }),
    ).rejects.toThrow(
      "NEXT_PUBLIC_API_URL is required in deployed environments and must point to the API/Render service",
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("throws when the server API base resolves to the app origin", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://app.example.test";
    global.fetch = vi.fn();

    await expect(
      loadExploreData({}, { app_base_url: "https://app.example.test/" }),
    ).rejects.toThrow(
      "NEXT_PUBLIC_API_URL must point to the API/Render service, not the app origin",
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("maps backend rows to compatibility aliases for existing components", async () => {
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
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";

    const data = await loadExploreData(
      { service: "roofing" },
      { app_base_url: "https://app.example.test" },
    );

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
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";

    await expect(
      loadExploreData({}, { app_base_url: "https://app.example.test" }),
    ).rejects.toThrow(
      "loadExploreData explore cities: HTTP 502",
    );
  });

  it("throws when the upstream request fails before a response is received", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("connection refused"));
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";

    await expect(
      loadExploreData({}, { app_base_url: "https://app.example.test" }),
    ).rejects.toThrow(
      "loadExploreData explore cities: connection refused",
    );
  });
});
