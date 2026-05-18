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

describe("GET /api/explore/cities", () => {
  it("forwards explore city filters and repeated states to FastAPI", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          cities: [],
          next_cursor: null,
          growth_available: false,
        }),
        { status: 200 },
      ),
    );
    global.fetch = fetchMock;

    const req = new Request(
      "http://localhost/api/explore/cities?service=roofing&state=AZ&state=CO&limit=25",
    );
    const res = await GET(req as never);

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({
      cities: [],
      next_cursor: null,
      growth_available: false,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/api/explore/cities?service=roofing&state=AZ&state=CO&limit=25",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("returns bounded 502 when FastAPI rejects the list request", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "x".repeat(800) }), {
        status: 503,
      }),
    );
    const req = new Request("http://localhost/api/explore/cities?service=roofing");

    const res = await GET(req as never);

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unavailable");
    expect(body.message).toHaveLength(500);
    expect(body.upstream_status).toBe(503);
    expect(body.upstream_detail).toHaveLength(500);
  });

  it("returns bounded 502 when fetch throws", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("n".repeat(800)));
    const req = new Request("http://localhost/api/explore/cities");

    const res = await GET(req as never);

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body).toMatchObject({
      status: "unavailable",
      message: "Explore cities service is unavailable.",
    });
    expect(body.error).toHaveLength(500);
  });
});
