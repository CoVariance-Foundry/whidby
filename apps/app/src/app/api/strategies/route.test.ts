import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  resolveEntitlementContext: vi.fn(),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: mocks.createClient,
}));

vi.mock("@/lib/account/entitlements", () => {
  class EntitlementError extends Error {
    constructor(
      message: string,
      public readonly status: number,
      public readonly code: string,
    ) {
      super(message);
    }
  }
  return {
    EntitlementError,
    resolveEntitlementContext: mocks.resolveEntitlementContext,
  };
});

import { EntitlementError } from "@/lib/account/entitlements";
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
  mocks.createClient.mockReset();
  mocks.resolveEntitlementContext.mockReset();
});

describe("GET /api/strategies", () => {
  function mockAuthenticatedUser() {
    mocks.createClient.mockResolvedValue({ auth: { getUser: vi.fn() } });
    mocks.resolveEntitlementContext.mockResolvedValue({
      user: { id: "user-1" },
      entitlement: { account_id: "account-1", plan_key: "free" },
    });
  }

  it("proxies to FastAPI and preserves the catalog response", async () => {
    mockAuthenticatedUser();
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
    expect(mocks.createClient).toHaveBeenCalledTimes(1);
    expect(mocks.resolveEntitlementContext).toHaveBeenCalledTimes(1);
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
    mockAuthenticatedUser();
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "bad catalog request" }), { status: 400 }),
    );
    global.fetch = fetchMock;

    const res = await GET();

    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ detail: "bad catalog request" });
  });

  it("requires authentication before proxying the strategy catalog", async () => {
    const authError = new EntitlementError("Sign in required.", 401, "auth_required");
    mocks.createClient.mockResolvedValue({ auth: { getUser: vi.fn() } });
    mocks.resolveEntitlementContext.mockRejectedValue(authError);
    global.fetch = vi.fn();

    const res = await GET();

    expect(res.status).toBe(401);
    expect(await res.json()).toEqual({
      status: "error",
      code: "auth_required",
      message: "Sign in required.",
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
