import { test, expect } from "@playwright/test";

test.describe("Exploration Surface (US2) -- API contract", () => {
  test("valid query returns score and evidence with snake_case keys", async ({
    request,
  }) => {
    const response = await request.post("/api/agent/exploration", {
      data: { city: "Phoenix", service: "roofing" },
    });
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.status).toBe("success");
    expect(body.score_result).toBeDefined();
    expect(body.score_result.opportunity_score).toBeGreaterThanOrEqual(0);
    expect(body.score_result.opportunity_score).toBeLessThanOrEqual(100);
    expect(body.evidence).toBeDefined();
    expect(body.evidence.length).toBeGreaterThanOrEqual(1);

    const firstEvidence = body.evidence[0];
    expect(firstEvidence.category).toBeTruthy();
    expect(firstEvidence.label).toBeTruthy();
    expect(firstEvidence.source).toBeTruthy();
    expect(firstEvidence.is_available).toBe(true);
  });

  test("empty input returns validation error", async ({ request }) => {
    const response = await request.post("/api/agent/exploration", {
      data: { city: "", service: "" },
    });
    expect(response.status()).toBe(400);

    const body = await response.json();
    expect(body.status).toBe("validation_error");
  });

  test("score parity with standard surface for same input", async ({
    request,
  }) => {
    const standardRes = await request.post("/api/agent/scoring", {
      data: { city: "Atlanta", service: "plumbing" },
    });
    const explorationRes = await request.post("/api/agent/exploration", {
      data: { city: "Atlanta", service: "plumbing" },
    });

    const standard = await standardRes.json();
    const exploration = await explorationRes.json();

    expect(standard.score_result.opportunity_score).toBe(
      exploration.score_result.opportunity_score
    );
    expect(standard.score_result.classification_label).toBe(
      exploration.score_result.classification_label
    );
  });

  test("evidence items all have required fields", async ({ request }) => {
    const response = await request.post("/api/agent/exploration", {
      data: { city: "Denver", service: "landscaping" },
    });
    const body = await response.json();

    for (const item of body.evidence) {
      expect(item).toHaveProperty("category");
      expect(item).toHaveProperty("label");
      expect(item).toHaveProperty("value");
      expect(item).toHaveProperty("source");
      expect(item).toHaveProperty("is_available");
    }
  });

  test("different inputs produce different scores", async ({ request }) => {
    const a = await request.post("/api/agent/exploration", {
      data: { city: "Phoenix", service: "roofing" },
    });
    const b = await request.post("/api/agent/exploration", {
      data: { city: "Seattle", service: "dentist" },
    });

    const bodyA = await a.json();
    const bodyB = await b.json();

    const scoresMatch =
      bodyA.score_result.opportunity_score ===
      bodyB.score_result.opportunity_score;
    expect(scoresMatch).toBe(false);
  });
});
