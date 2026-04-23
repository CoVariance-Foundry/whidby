import { describe, expect, it, vi } from "vitest";
import { GET } from "./route";
import { NextRequest } from "next/server";

describe("GET /api/agent/places/suggest", () => {
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
});
