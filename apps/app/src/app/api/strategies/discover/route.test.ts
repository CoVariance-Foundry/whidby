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
import { POST } from "./route";

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

describe("POST /api/strategies/discover", () => {
  function mockAuthenticatedUser() {
    mocks.createClient.mockResolvedValue({ auth: { getUser: vi.fn() } });
    mocks.resolveEntitlementContext.mockResolvedValue({
      user: { id: "user-1" },
      entitlement: { account_id: "account-1", plan_key: "free" },
    });
  }

  it("proxies the request body to FastAPI /api/discover", async () => {
    mockAuthenticatedUser();
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    const responseBody = {
      markets: [{ rank: 1, lens_id: "keyword_hijack" }],
      total: 1,
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), { status: 200 }),
    );
    global.fetch = fetchMock;
    const payload = {
      lens_id: "keyword_hijack",
      primary_keyword: "boise plumber",
      city_filters: [{ field: "state", operator: "eq", value: "ID" }],
      limit: 10,
    };
    const req = new Request("http://localhost/api/strategies/discover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual(responseBody);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(mocks.createClient).toHaveBeenCalledTimes(1);
    expect(mocks.resolveEntitlementContext).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("https://api.example.test/api/discover");
    expect(fetchMock.mock.calls[0][1]).toEqual({
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
  });

  it("preserves upstream validation statuses", async () => {
    mockAuthenticatedUser();
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "reference_city_id not yet supported" }), {
        status: 400,
      }),
    );
    global.fetch = fetchMock;
    const req = new Request("http://localhost/api/strategies/discover", {
      method: "POST",
      body: JSON.stringify({ lens_id: "expand_conquer", reference_city_id: "boise-id" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({
      detail: "reference_city_id not yet supported",
    });
  });

  it("requires authentication before proxying cached discovery", async () => {
    mocks.createClient.mockResolvedValue({ auth: { getUser: vi.fn() } });
    mocks.resolveEntitlementContext.mockRejectedValue(
      new EntitlementError("Authentication required.", 401, "auth_required"),
    );
    global.fetch = vi.fn();
    const req = new Request("http://localhost/api/strategies/discover", {
      method: "POST",
      body: JSON.stringify({ lens_id: "easy_win" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(401);
    expect(await res.json()).toMatchObject({
      code: "auth_required",
      message: "Authentication required.",
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
