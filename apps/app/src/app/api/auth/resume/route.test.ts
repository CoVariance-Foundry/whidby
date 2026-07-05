import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: mocks.createClient,
}));

import { GET } from "./route";

describe("GET /api/auth/resume", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns 401 when no signed-in user exists", async () => {
    const supabase = createSupabaseMock({
      userResult: {
        data: { user: null },
        error: { message: "missing session" },
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/api/auth/resume"));
    const body = await res.json();

    expect(res.status).toBe(401);
    expect(body).toEqual({ status: "error", next: "/login" });
    expect(supabase.from).not.toHaveBeenCalled();
  });

  it("returns explicit safe next before profile resume routing", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status: "strategy_recommended",
          intent: "scale",
          next_route: "/strategies",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(
      new Request("http://localhost/api/auth/resume?next=/reports/abc"),
    );
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", next: "/reports/abc" });
    expect(supabase.from).not.toHaveBeenCalled();
  });

  it("treats root next as resumable segment routing", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status: "strategy_recommended",
          intent: "scale",
          next_route: "/",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(
      new Request("http://localhost/api/auth/resume?next=/"),
    );
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", next: "/strategies" });
    expect(supabase.profileEq).toHaveBeenCalledWith("user_id", "user-1");
  });

  it("routes strategy-recommended scale users to strategies", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status: "strategy_recommended",
          intent: "scale",
          next_route: "/",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/api/auth/resume"));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", next: "/strategies" });
  });

  it("routes strategy-recommended agency users to agency", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status: "strategy_recommended",
          intent: "coach_agency",
          next_route: "/strategies",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/api/auth/resume"));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", next: "/agency" });
  });

  it("keeps incomplete profiles in onboarding", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status: "target_selected",
          intent: "scale",
          next_route: "/strategies",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/api/auth/resume"));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", next: "/onboarding" });
  });

  it("returns cached safe routes", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status: "cached_route_selected",
          intent: "scale",
          next_route: "/explore",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/api/auth/resume"));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", next: "/explore" });
  });

  it("falls back to onboarding for unsafe cached routes", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status: "cached_route_selected",
          intent: "scale",
          next_route: "//evil.example",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/api/auth/resume"));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", next: "/onboarding" });
  });

  it("routes users without an onboarding profile to onboarding", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: null,
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/api/auth/resume"));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", next: "/onboarding" });
  });

  it("falls back to onboarding when profile lookup fails", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    const supabase = createSupabaseMock({
      profileResult: {
        data: null,
        error: { message: "profile lookup failed" },
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/api/auth/resume"));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", next: "/onboarding" });
    expect(consoleError).toHaveBeenCalledWith(
      "[auth/resume] onboarding profile lookup failed",
      { message: "profile lookup failed" },
    );
  });

  it("ignores unsafe next values", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status: "strategy_recommended",
          intent: "researching",
          next_route: "/explore",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(
      new Request("http://localhost/api/auth/resume?next=//evil.example"),
    );
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body).toEqual({ status: "success", next: "/explore" });
  });
});

type QueryResult = {
  data: unknown;
  error: { message: string } | null;
};

function createSupabaseMock(options: {
  userResult?: {
    data: {
      user: { id: string } | null;
    };
    error: {
      message: string;
      status?: number;
      code?: string;
      name?: string;
    } | null;
  };
  profileResult?: QueryResult;
} = {}) {
  const profileResult = options.profileResult ?? { data: null, error: null };
  const profileMaybeSingle = vi.fn().mockResolvedValue(profileResult);
  const profileEq = vi.fn(() => ({ maybeSingle: profileMaybeSingle }));
  const profileSelect = vi.fn(() => ({ eq: profileEq }));

  return {
    auth: {
      getUser: vi.fn().mockResolvedValue(
        options.userResult ?? {
          data: { user: { id: "user-1" } },
          error: null,
        },
      ),
    },
    from: vi.fn((table: string) => {
      if (table === "onboarding_profiles") {
        return {
          select: profileSelect,
        };
      }
      throw new Error(`Unexpected table ${table}`);
    }),
    profileEq,
    profileMaybeSingle,
  };
}
