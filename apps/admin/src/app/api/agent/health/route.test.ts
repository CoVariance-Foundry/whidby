import { describe, expect, it, vi } from "vitest";
import { GET } from "./route";

describe("GET /api/agent/health", () => {
  it("returns ok when FastAPI /health returns ok", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
    );
    const res = await GET();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.status).toBe("ok");
    expect(body.upstream).toBe("ok");
  });

  it("returns unavailable with upstream_status when FastAPI is down", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("ECONNREFUSED"));
    const res = await GET();
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unavailable");
    expect(body.error).toContain("ECONNREFUSED");
  });
});
