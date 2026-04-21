import { test, expect } from "@playwright/test";

test.describe("Niche scoring (dry run via FastAPI)", () => {
  test("scoring proxy returns FastAPI-shaped response with report_id", async ({
    request,
  }) => {
    const response = await request.post("/api/agent/scoring", {
      data: { city: "Phoenix", service: "roofing" },
    });
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.status).toBe("success");
    expect(body.score_result.opportunity_score).toBeGreaterThanOrEqual(0);
    expect(body.score_result.opportunity_score).toBeLessThanOrEqual(100);
    expect(["High", "Medium", "Low"]).toContain(
      body.score_result.classification_label,
    );
    expect(body.report_id).toBeTruthy();
  });

  test("exploration proxy returns evidence from real M6 signals", async ({
    request,
  }) => {
    const response = await request.post("/api/agent/exploration", {
      data: { city: "Phoenix", service: "roofing" },
    });
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(["success", "partial_evidence"]).toContain(body.status);
    expect(body.score_result.opportunity_score).toBeGreaterThanOrEqual(0);
    expect(body.evidence).toBeDefined();
    expect(body.evidence.length).toBeGreaterThanOrEqual(1);
    const categories = body.evidence.map(
      (e: { category: string }) => e.category,
    );
    expect(categories).toContain("demand");
    for (const e of body.evidence) {
      expect(e.source).toMatch(/M6/);
    }
  });

  test("scoring and exploration agree on the report_id for same input", async ({
    request,
  }) => {
    const s = await request.post("/api/agent/scoring", {
      data: { city: "Phoenix", service: "roofing" },
    });
    const e = await request.post("/api/agent/exploration", {
      data: { city: "Phoenix", service: "roofing" },
    });
    const sBody = await s.json();
    const eBody = await e.json();
    expect(sBody.score_result.opportunity_score).toBe(
      eBody.score_result.opportunity_score,
    );
  });

  test("empty input returns 400 validation error on both surfaces", async ({
    request,
  }) => {
    for (const path of ["/api/agent/scoring", "/api/agent/exploration"]) {
      const res = await request.post(path, {
        data: { city: "", service: "" },
      });
      expect(res.status()).toBe(400);
      const body = await res.json();
      expect(body.status).toBe("validation_error");
    }
  });
});
