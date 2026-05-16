import { afterEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";

const originalFetch = global.fetch;
const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;

afterEach(() => {
  global.fetch = originalFetch;
  if (originalApiUrl === undefined) {
    delete process.env.NEXT_PUBLIC_API_URL;
  } else {
    process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
  }
  vi.restoreAllMocks();
});

describe("GET /api/strategies", () => {
  it("proxies to FastAPI and preserves the catalog response", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    const catalog = {
      strategies: [
        {
          strategy_id: "easy_win",
          name: "Easy Win",
          description: "Weak competition markets.",
          status: "launch",
          input_shape: "city_service",
        },
        {
          strategy_id: "cash_cow",
          name: "Cash Cow",
          description: "Cached scan strategy.",
          status: "phase_2",
          input_shape: "cached_scan",
        },
      ],
      global_modifiers: [
        {
          modifier_id: "ai_resilience",
          name: "AI Resilience",
          behavior: "warn_not_hide",
        },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(catalog), { status: 200 }),
    );
    global.fetch = fetchMock;

    const res = await GET();

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual(catalog);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/api/strategies",
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      },
    );
  });

  it("preserves upstream client error statuses", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "bad catalog request" }), { status: 400 }),
    );
    global.fetch = fetchMock;

    const res = await GET();

    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ detail: "bad catalog request" });
  });
});
