import { describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET } from "./route";

describe("GET /api/agent/reports/[reportId]", () => {
  it("maps upstream niche payload into report detail shape", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          report_id: "r1",
          generated_at: "2026-05-14T18:00:00Z",
          spec_version: "1.1",
          input: {
            niche_keyword: "roofing",
            geo_scope: "city",
            geo_target: "Phoenix, AZ",
            report_depth: "standard",
            strategy_profile: "balanced",
          },
          keyword_expansion: { expanded_keywords: [] },
          metros: [],
          meta: { total_api_calls: 7 },
        }),
        { status: 200 },
      ),
    );

    const req = new NextRequest("http://localhost/api/agent/reports/r1");
    const res = await GET(req, { params: { reportId: "r1" } });
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.status).toBe("success");
    expect(body.report).toMatchObject({
      id: "r1",
      niche_keyword: "roofing",
      geo_target: "Phoenix, AZ",
      strategy_profile: "balanced",
    });
  });

  it("returns 502 envelope when upstream request fails", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "report not found" }), { status: 404 }),
    );

    const req = new NextRequest("http://localhost/api/agent/reports/missing");
    const res = await GET(req, { params: { reportId: "missing" } });
    const body = await res.json();

    expect(res.status).toBe(502);
    expect(body.status).toBe("unavailable");
    expect(body.upstream_status).toBe(404);
  });
});
