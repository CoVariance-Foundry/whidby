import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";

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

describe("POST /api/explore/refresh/runs", () => {
  it("proxies the manual refresh body to FastAPI and maps success", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ run_id: "manual-run-1", status: "queued" }),
        { status: 200 },
      ),
    );
    global.fetch = fetchMock;

    const payload = {
      scope: "visible",
      target_ids: ["target-1"],
      report_ids: ["report-1"],
      filters: { state: "AZ", min_opportunity_score: 70 },
      flags: {
        force: true,
        dry_run: true,
        strategy_profile: "growth",
        max_items: 25,
        concurrency: 3,
      },
    };
    const requestBody = JSON.stringify(payload);
    const req = new Request("http://localhost/api/explore/refresh/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: requestBody,
    });

    const res = await POST(req as never);

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({
      run_id: "manual-run-1",
      status: "queued",
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe(
      "https://api.example.test/api/explore/refresh/runs",
    );
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(init.body).toBe(requestBody);
  });

  it("returns 502 with upstream details when FastAPI rejects the run", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "refresh store unavailable" }), {
        status: 503,
      }),
    );
    const req = new Request("http://localhost/api/explore/refresh/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scope: "selected",
        target_ids: ["target-1"],
        flags: { dry_run: true },
      }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unavailable");
    expect(body.message).toBe("refresh store unavailable");
    expect(body.upstream_status).toBe(503);
    expect(body.upstream_detail).toBe("refresh store unavailable");
  });

  it("returns validation_error for invalid JSON without proxying upstream", async () => {
    const fetchMock = vi.fn();
    global.fetch = fetchMock;
    const req = new Request("http://localhost/api/explore/refresh/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{",
    });

    const res = await POST(req as never);

    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({
      status: "validation_error",
      message: "Invalid JSON body.",
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("caps upstream JSON error fields before returning 502", async () => {
    const longDetail = "x".repeat(800);
    const longMessage = "m".repeat(800);
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: longDetail,
          message: longMessage,
          error: { reason: "e".repeat(800) },
        }),
        { status: 500 },
      ),
    );
    const req = new Request("http://localhost/api/explore/refresh/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope: "stale" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.message).toHaveLength(500);
    expect(body.upstream_detail).toHaveLength(500);
    expect(body.upstream_message).toHaveLength(500);
    expect(body.upstream_error).toHaveLength(500);
  });

  it("caps oversized upstream plain-text errors before returning 502", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response("p".repeat(10000), { status: 500 }),
    );
    const req = new Request("http://localhost/api/explore/refresh/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope: "stale" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.message).toHaveLength(500);
    expect(body.upstream_body).toHaveLength(500);
  });

  it("caps thrown network error details before returning 502", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("n".repeat(800)));
    const req = new Request("http://localhost/api/explore/refresh/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope: "stale" }),
    });

    const res = await POST(req as never);

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unavailable");
    expect(body.error).toHaveLength(500);
  });
});
