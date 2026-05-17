import { beforeEach, describe, expect, it, vi } from "vitest";
import { __resetPlacesSuggestCacheForTests, GET } from "./route";
import { NextRequest } from "next/server";

describe("GET /api/agent/places/suggest", () => {
  beforeEach(() => {
    __resetPlacesSuggestCacheForTests();
    vi.restoreAllMocks();
  });

  it("forwards q + limit and returns the upstream list verbatim", async () => {
    const sample = [
      { city: "Phoenix", region: "AZ", country: "US" },
    ];
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(sample), { status: 200 }),
    );
    global.fetch = fetchMock;

    const req = new NextRequest("http://localhost/api/agent/places/suggest?q=phoe&limit=5");
    const res = await GET(req);

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual(sample);
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("/api/places/suggest?q=phoe");
    expect(calledUrl).toContain("limit=5");
  });

  it("returns cached data for repeated q + limit requests", async () => {
    const sample = [{ city: "St Louis", region: "MO", country: "US" }];
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(sample), { status: 200 }),
    );
    global.fetch = fetchMock;

    const req1 = new NextRequest("http://localhost/api/agent/places/suggest?q=st%20l&limit=8");
    const res1 = await GET(req1);
    expect(res1.status).toBe(200);
    expect(await res1.json()).toEqual(sample);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const req2 = new NextRequest("http://localhost/api/agent/places/suggest?q=st%20l&limit=8");
    const res2 = await GET(req2);
    expect(res2.status).toBe(200);
    expect(await res2.json()).toEqual(sample);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("returns 502 with upstream details when FastAPI errors", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "seed missing" }), { status: 500 }),
    );

    const req = new NextRequest("http://localhost/api/agent/places/suggest?q=phoe");
    const res = await GET(req);
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unavailable");
    expect(body.upstream_status).toBe(500);
  });

  it("returns timeout envelope when upstream fetch aborts", async () => {
    global.fetch = vi.fn().mockRejectedValue(new DOMException("aborted", "AbortError"));
    const req = new NextRequest("http://localhost/api/agent/places/suggest?q=phoe");
    const res = await GET(req);
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unavailable");
    expect(body.error).toContain("timed out");
  });
});
