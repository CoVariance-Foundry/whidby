import { describe, expect, it, vi } from "vitest";
import { POST } from "./route";

describe("POST /api/agent/exploration", () => {
  it("proxies to FastAPI and returns score_result plus evidence", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        report_id: "r3",
        opportunity_score: 68,
        classification_label: "Medium",
        evidence: [
          { category: "demand", label: "x", value: 100, source: "M6", is_available: true },
        ],
        report: { input: { niche_keyword: "roofing" } },
      }), { status: 200 }),
    );
    const req = new Request("http://localhost/api/agent/exploration", {
      method: "POST",
      body: JSON.stringify({ city: "Phoenix", service: "roofing" }),
    });
    const res = await POST(req as never);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.score_result.opportunity_score).toBe(68);
    expect(body.evidence.length).toBe(1);
    expect(body.evidence[0].source).toBe("M6");
    expect(body.status).toBe("success");
  });
});
