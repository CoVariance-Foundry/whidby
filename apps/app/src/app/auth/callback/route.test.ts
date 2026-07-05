import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: mocks.createClient,
}));

import { GET } from "./route";

describe("GET /auth/callback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env.NEXT_PUBLIC_APP_FRONTEND_URL;
  });

  it("redirects to login error when no code is supplied", async () => {
    const res = await GET(new Request("http://localhost/auth/callback"));

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe(
      "http://localhost/login?error=auth_callback_failed&reason=no_code",
    );
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("redirects to login error when code exchange fails", async () => {
    const supabase = createSupabaseMock({
      exchangeResult: {
        error: {
          message: "Code verifier mismatch.",
          status: 400,
          code: "bad_code",
          name: "AuthApiError",
        },
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/auth/callback?code=bad"));

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe(
      "http://localhost/login?error=auth_callback_failed&reason=bad_code",
    );
    expect(supabase.auth.getUser).not.toHaveBeenCalled();
    expect(supabase.from).not.toHaveBeenCalled();
  });

  it("redirects to an explicit safe next after successful exchange", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: null,
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(
      new Request("http://localhost/auth/callback?code=ok&next=/reports/abc"),
    );

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/reports/abc");
    expect(supabase.profileEq).toHaveBeenCalledWith("user_id", "user-1");
  });

  it("redirects to onboarding after success when no profile exists", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: null,
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/auth/callback?code=ok"));

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/onboarding");
  });

  it("redirects strategy_recommended profiles through their canonical segment route", async () => {
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

    const res = await GET(new Request("http://localhost/auth/callback?code=ok"));

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/strategies");
  });

  it("uses persisted intent before stale stored routes", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status: "strategy_recommended",
          intent: "find_first",
          next_route: "/strategies",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/auth/callback?code=ok"));

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/");
  });

  it("returns cached-route research users to Explore", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status: "cached_route_selected",
          intent: "researching",
          next_route: "/explore",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/auth/callback?code=ok"));

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/explore");
  });

  it("ignores unsafe next and applies onboarding resume logic", async () => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status: "target_selected",
          intent: "scale",
          next_route: "/onboarding",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(
      new Request("http://localhost/auth/callback?code=ok&next=//evil.example"),
    );

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/onboarding");
  });

  it("keeps target_selected users in onboarding even when the stored next_route is a strategy page", async () => {
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

    const res = await GET(new Request("http://localhost/auth/callback?code=ok"));

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/onboarding");
  });

  it.each([
    "report_queued",
    "upgrade_required",
    "report_ready",
  ])("redirects terminal onboarding status %s to reports", async (status) => {
    const supabase = createSupabaseMock({
      profileResult: {
        data: {
          status,
          intent: "find_first",
          next_route: "/onboarding",
        },
        error: null,
      },
    });
    mocks.createClient.mockResolvedValue(supabase);

    const res = await GET(new Request("http://localhost/auth/callback?code=ok"));

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost/reports");
  });
});

type QueryResult = {
  data: unknown;
  error: { message: string } | null;
};

function createSupabaseMock(options: {
  exchangeResult?: {
    error: {
      message: string;
      status?: number;
      code?: string;
      name?: string;
    } | null;
  };
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
      exchangeCodeForSession: vi
        .fn()
        .mockResolvedValue(options.exchangeResult ?? { error: null }),
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
