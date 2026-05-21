import { afterEach, describe, expect, it, vi } from "vitest";
import { loadDashboard } from "./load-dashboard";

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("loadDashboard", () => {
  it("loads dashboard DTOs from the reports BFF route", async () => {
    const dashboard = {
      stats: {
        total_reports: 2,
        avg_score: 75,
        watchlist: 0,
        niches_scored: 2,
      },
      recent: [
        {
          id: "r1",
          niche: "roofing",
          city: "Phoenix, AZ",
          created_at: "2026-04-20T12:00:00Z",
        },
      ],
      recommended: [
        {
          id: "r1",
          niche: "roofing",
          city: "Phoenix, AZ",
          score: 78,
        },
      ],
      stat_cards: [
        { label: "Niches scored", value: "2" },
        { label: "Watchlist", value: "0" },
        { label: "Avg score", value: "75" },
        { label: "Reports", value: "2" },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "success", dashboard }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    global.fetch = fetchMock;

    await expect(
      loadDashboard({ app_base_url: "https://app.example.test/" }),
    ).resolves.toEqual(dashboard);

    expect(fetchMock).toHaveBeenCalledWith(
      "https://app.example.test/api/agent/reports?view=dashboard&limit=10",
      { cache: "no-store" },
    );
  });

  it("throws a bounded loader error when the BFF route rejects the request", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "unavailable" }), { status: 502 }),
    );

    await expect(
      loadDashboard({ app_base_url: "https://app.example.test" }),
    ).rejects.toThrow("loadDashboard: HTTP 502");
  });

  it("throws when the reports BFF response is malformed", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "success" }), { status: 200 }),
    );

    await expect(
      loadDashboard({ app_base_url: "https://app.example.test" }),
    ).rejects.toThrow("loadDashboard: invalid response");
  });
});
