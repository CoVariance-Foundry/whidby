import { describe, expect, it, vi } from "vitest";
import { POST } from "./route";

describe("POST /api/agent/scoring", () => {
  it("proxies to FastAPI and maps the response", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        report_id: "r1",
        opportunity_score: 72,
        classification_label: "Medium",
        evidence: [],
        report: { input: { niche_keyword: "roofing" } },
      }), { status: 200 }),
    );
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing", state: "AZ" }),
    });
    const res = await POST(req as never);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.score_result.opportunity_score).toBe(72);
    expect(body.score_result.classification_label).toBe("Medium");
    expect(body.report_id).toBe("r1");
    expect(body.query).toEqual({ city: "Phoenix", service: "roofing", state: "AZ" });
  });

  it("passes dry_run=true when NEXT_PUBLIC_NICHE_DRY_RUN=1", async () => {
    process.env.NEXT_PUBLIC_NICHE_DRY_RUN = "1";
    const spy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ report_id: "r2", opportunity_score: 50,
        classification_label: "Medium", evidence: [], report: { input: { niche_keyword: "x" }}}), { status: 200 }),
    );
    global.fetch = spy;
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing", state: "AZ" }),
    });
    await POST(req as never);
    const sent = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(sent.dry_run).toBe(true);
    delete process.env.NEXT_PUBLIC_NICHE_DRY_RUN;
  });

  it("forwards place_id and dataforseo_location_code when provided", async () => {
    const spy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        report_id: "r3",
        opportunity_score: 81,
        classification_label: "High",
        evidence: [],
        report: { input: { niche_keyword: "roofing" } },
      }), { status: 200 }),
    );
    global.fetch = spy;
    const req = new Request("http://localhost/api/agent/scoring", {
      method: "POST",
      body: JSON.stringify({
        city: "Paris",
        service: "roofing",
        place_id: "place.123",
        dataforseo_location_code: 12345,
      }),
    });
    await POST(req as never);

    const sent = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(sent.place_id).toBe("place.123");
    expect(sent.dataforseo_location_code).toBe(12345);
  });
});
