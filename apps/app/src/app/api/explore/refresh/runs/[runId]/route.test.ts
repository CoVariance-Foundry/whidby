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

describe("GET /api/explore/refresh/runs/[runId]", () => {
  it("proxies run status to FastAPI and returns the upstream payload", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    const upstreamPayload = {
      run_id: "run/with space",
      status: "running",
      items: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(upstreamPayload), { status: 200 }),
    );
    global.fetch = fetchMock;

    const res = await GET(
      new Request("http://localhost/api/explore/refresh/runs/run%2Fwith%20space") as never,
      { params: Promise.resolve({ runId: "run/with space" }) },
    );

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual(upstreamPayload);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe(
      "https://api.example.test/api/explore/refresh/runs/run%2Fwith%20space",
    );
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("GET");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
  });

  it("returns bounded unavailable details when upstream status lookup fails", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "d".repeat(800) }), {
        status: 503,
      }),
    );

    const res = await GET(
      new Request("http://localhost/api/explore/refresh/runs/run-1") as never,
      { params: Promise.resolve({ runId: "run-1" }) },
    );

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unavailable");
    expect(body.upstream_status).toBe(503);
    expect(body.message).toHaveLength(500);
    expect(body.upstream_detail).toHaveLength(500);
  });
});
