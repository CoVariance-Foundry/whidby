import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const mockGetUser = vi.fn();
const mockCreateServerClient = vi.fn();

vi.mock("@supabase/ssr", () => ({
  createServerClient: (...args: unknown[]) => mockCreateServerClient(...args),
}));

const mockRedirect = vi.fn();
const mockNext = vi.fn();

vi.mock("next/server", () => {
  const cookies = {
    getAll: vi.fn(() => []),
    set: vi.fn(),
  };

  class MockNextRequest {
    cookies = cookies;
    nextUrl: {
      pathname: string;
      search: string;
      searchParams: URLSearchParams;
      clone: () => MockNextRequest["nextUrl"];
    };

    constructor(url: string) {
      const parsed = new URL(url, "http://localhost:3001");
      this.nextUrl = {
        pathname: parsed.pathname,
        search: parsed.search,
        searchParams: parsed.searchParams,
        clone() {
          return { ...this };
        },
      };
    }
  }

  const NextResponseClass = {
    next: (opts?: unknown) => {
      const res = {
        type: "next",
        opts,
        cookies: { set: vi.fn(), getAll: () => [] },
      };
      mockNext(res);
      return res;
    },
    redirect: (url: unknown) => {
      const res = { type: "redirect", url, cookies: { set: vi.fn() } };
      mockRedirect(res);
      return res;
    },
  };

  return {
    NextResponse: NextResponseClass,
    NextRequest: MockNextRequest,
  };
});

async function makeRequest(path: string) {
  const { NextRequest } = await import("next/server");
  return new NextRequest(`http://localhost:3001${path}`);
}

function setupSupabaseClient(user: unknown | null) {
  mockCreateServerClient.mockReturnValue({
    auth: {
      getUser: mockGetUser.mockResolvedValue({
        data: { user },
      }),
    },
  });
}

const originalEnv = { ...process.env };

describe("proxy", () => {
  beforeEach(() => {
    vi.resetModules();
    mockCreateServerClient.mockReset();
    mockGetUser.mockReset();
    mockRedirect.mockClear();
    mockNext.mockClear();
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://test.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY = "test-key";
  });

  afterEach(() => {
    process.env = { ...originalEnv };
  });

  it("redirects protected route to /login when NEXT_PUBLIC_SUPABASE_URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    const { proxy } = await import("../proxy");
    const req = await makeRequest("/dashboard");
    const res = await proxy(req);

    expect(res.type).toBe("redirect");
    expect(res.url.pathname).toBe("/login");
    expect(mockCreateServerClient).not.toHaveBeenCalled();
  });

  it("redirects protected route to /login when publishable key is missing", async () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY;
    const { proxy } = await import("../proxy");
    const req = await makeRequest("/");
    const res = await proxy(req);

    expect(res.type).toBe("redirect");
    expect(res.url.pathname).toBe("/login");
    expect(mockCreateServerClient).not.toHaveBeenCalled();
  });

  it("redirects unauthenticated user to /login on protected route", async () => {
    setupSupabaseClient(null);
    const { proxy } = await import("../proxy");
    const req = await makeRequest("/dashboard");
    const res = await proxy(req);

    expect(res.type).toBe("redirect");
    expect(res.url.pathname).toBe("/login");
  });

  it("redirects authenticated user from /login to /", async () => {
    setupSupabaseClient({ id: "user-1", email: "test@example.com" });
    const { proxy } = await import("../proxy");
    const req = await makeRequest("/login");
    const res = await proxy(req);

    expect(res.type).toBe("redirect");
    expect(res.url.pathname).toBe("/");
  });

  it("allows unauthenticated user to access /login", async () => {
    setupSupabaseClient(null);
    const { proxy } = await import("../proxy");
    const req = await makeRequest("/login");
    const res = await proxy(req);

    expect(res.type).toBe("next");
  });

  it("allows unauthenticated user to access /auth/callback", async () => {
    setupSupabaseClient(null);
    const { proxy } = await import("../proxy");
    const req = await makeRequest("/auth/callback?code=abc");
    const res = await proxy(req);

    expect(res.type).toBe("next");
    expect(mockCreateServerClient).not.toHaveBeenCalled();
  });

  it("allows authenticated user to access protected route", async () => {
    setupSupabaseClient({ id: "user-1", email: "test@example.com" });
    const { proxy } = await import("../proxy");
    const req = await makeRequest("/dashboard");
    const res = await proxy(req);

    expect(res.type).toBe("next");
  });

  it("redirects protected route to /login when getUser throws", async () => {
    mockCreateServerClient.mockReturnValue({
      auth: {
        getUser: vi.fn().mockRejectedValue(new Error("Network failure")),
      },
    });
    const { proxy } = await import("../proxy");
    const req = await makeRequest("/dashboard");
    const res = await proxy(req);

    expect(res.type).toBe("redirect");
    expect(res.url.pathname).toBe("/login");
  });

  it("redirects protected route to /login when createServerClient throws", async () => {
    mockCreateServerClient.mockImplementation(() => {
      throw new Error("Invalid URL");
    });
    const { proxy } = await import("../proxy");
    const req = await makeRequest("/");
    const res = await proxy(req);

    expect(res.type).toBe("redirect");
    expect(res.url.pathname).toBe("/login");
  });
});
