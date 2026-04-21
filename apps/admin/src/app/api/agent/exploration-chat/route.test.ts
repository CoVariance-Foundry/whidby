import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { POST } from "./route";

describe("POST /api/agent/exploration-chat", () => {
  const originalFetch = global.fetch;
  beforeEach(() => { vi.restoreAllMocks(); });
  afterEach(() => { global.fetch = originalFetch; });

  it("returns upstream_status and upstream_body when FastAPI returns 500", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "agent crashed" }), { status: 500 }),
    );
    const req = new Request("http://localhost/api/agent/exploration-chat", {
      method: "POST",
      body: JSON.stringify({
        query_context: { city: "Phoenix", service: "roofing" },
        question: "why",
        session_id: "s1",
      }),
    });
    const res = await POST(req as never);
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unsupported");
    expect(body.upstream_status).toBe(500);
    expect(body.upstream_body).toContain("agent crashed");
  });
});
