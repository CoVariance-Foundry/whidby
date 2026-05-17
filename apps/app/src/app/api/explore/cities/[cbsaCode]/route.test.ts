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

describe("GET /api/explore/cities/[cbsaCode]", () => {
  it("forwards encoded cbsaCode to FastAPI and returns JSON", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    const payload = {
      cbsa_code: "123/45",
      cbsa_name: "Test Metro",
      cached_scores: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );
    global.fetch = fetchMock;

    const res = await GET(new Request("http://localhost/api/explore/cities/123%2F45") as never, {
      params: { cbsaCode: "123/45" },
    });

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/api/explore/cities/123%2F45",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("preserves FastAPI 404 JSON detail", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "City not found" }), {
        status: 404,
      }),
    );

    const res = await GET(new Request("http://localhost/api/explore/cities/99999") as never, {
      params: Promise.resolve({ cbsaCode: "99999" }),
    });

    expect(res.status).toBe(404);
    expect(await res.json()).toEqual({ detail: "City not found" });
  });

  it("returns bounded 502 when FastAPI rejects the detail request", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ message: "m".repeat(800) }), {
        status: 500,
      }),
    );

    const res = await GET(new Request("http://localhost/api/explore/cities/99999") as never, {
      params: { cbsaCode: "99999" },
    });

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unavailable");
    expect(body.message).toHaveLength(500);
    expect(body.upstream_status).toBe(500);
  });
});
