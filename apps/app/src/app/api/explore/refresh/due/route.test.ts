import { afterEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";

const originalFetch = global.fetch;
const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;
const originalCronSecret = process.env.CRON_SECRET;
const originalExploreCronSecret = process.env.EXPLORE_REFRESH_CRON_SECRET;

afterEach(() => {
  global.fetch = originalFetch;
  if (originalApiUrl === undefined) {
    delete process.env.NEXT_PUBLIC_API_URL;
  } else {
    process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
  }
  if (originalCronSecret === undefined) {
    delete process.env.CRON_SECRET;
  } else {
    process.env.CRON_SECRET = originalCronSecret;
  }
  if (originalExploreCronSecret === undefined) {
    delete process.env.EXPLORE_REFRESH_CRON_SECRET;
  } else {
    process.env.EXPLORE_REFRESH_CRON_SECRET = originalExploreCronSecret;
  }
  vi.restoreAllMocks();
});

describe("GET /api/explore/refresh/due", () => {
  it("accepts Vercel cron Authorization and forwards x-cron-secret upstream", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    process.env.CRON_SECRET = "vercel-secret";
    delete process.env.EXPLORE_REFRESH_CRON_SECRET;
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ run_id: "due-run-1", status: "queued" }), {
        status: 200,
      }),
    );
    global.fetch = fetchMock;

    const req = new Request("http://localhost/api/explore/refresh/due", {
      method: "GET",
      headers: { authorization: "Bearer vercel-secret" },
    });

    const res = await GET(req as never);

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({
      run_id: "due-run-1",
      status: "queued",
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe(
      "https://api.example.test/api/explore/refresh/due",
    );
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({
      "Content-Type": "application/json",
      "x-cron-secret": "vercel-secret",
    });
  });

  it("accepts local x-cron-secret and forwards it upstream", async () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test";
    delete process.env.CRON_SECRET;
    process.env.EXPLORE_REFRESH_CRON_SECRET = "local-secret";
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ run_id: "due-run-local", status: "queued" }), {
        status: 200,
      }),
    );
    global.fetch = fetchMock;

    const req = new Request("http://localhost/api/explore/refresh/due", {
      method: "GET",
      headers: { "x-cron-secret": "local-secret" },
    });

    const res = await GET(req as never);

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({
      run_id: "due-run-local",
      status: "queued",
    });
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.headers).toEqual({
      "Content-Type": "application/json",
      "x-cron-secret": "local-secret",
    });
  });

  it("rejects when a cron secret is configured and auth is missing or wrong", async () => {
    process.env.CRON_SECRET = "vercel-secret";
    delete process.env.EXPLORE_REFRESH_CRON_SECRET;
    const fetchMock = vi.fn();
    global.fetch = fetchMock;

    const missing = await GET(
      new Request("http://localhost/api/explore/refresh/due", {
        method: "GET",
      }) as never,
    );
    const wrong = await GET(
      new Request("http://localhost/api/explore/refresh/due", {
        method: "GET",
        headers: { authorization: "Bearer wrong-secret" },
      }) as never,
    );

    expect(missing.status).toBe(401);
    expect(await missing.json()).toEqual({ status: "unauthorized" });
    expect(wrong.status).toBe(401);
    expect(await wrong.json()).toEqual({ status: "unauthorized" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects as misconfigured when no cron secret is configured", async () => {
    delete process.env.CRON_SECRET;
    delete process.env.EXPLORE_REFRESH_CRON_SECRET;
    const fetchMock = vi.fn();
    global.fetch = fetchMock;

    const res = await GET(
      new Request("http://localhost/api/explore/refresh/due", {
        method: "GET",
      }) as never,
    );

    expect(res.status).toBe(503);
    expect(await res.json()).toEqual({
      status: "misconfigured",
      message: "Cron secret is not configured.",
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("caps thrown network error details before returning 502", async () => {
    process.env.CRON_SECRET = "vercel-secret";
    delete process.env.EXPLORE_REFRESH_CRON_SECRET;
    global.fetch = vi.fn().mockRejectedValue(new Error("n".repeat(800)));

    const res = await GET(
      new Request("http://localhost/api/explore/refresh/due", {
        method: "GET",
        headers: { authorization: "Bearer vercel-secret" },
      }) as never,
    );

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.status).toBe("unavailable");
    expect(body.error).toHaveLength(500);
  });

  it("caps upstream JSON errors without using Response.text", async () => {
    process.env.CRON_SECRET = "vercel-secret";
    delete process.env.EXPLORE_REFRESH_CRON_SECRET;
    const textSpy = vi.fn(() => {
      throw new Error("Response.text should not be called");
    });
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            JSON.stringify({ detail: "d".repeat(800), message: "m".repeat(800) }),
          ),
        );
        controller.close();
      },
    });
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      body: stream,
      text: textSpy,
    } as unknown as Response);

    const res = await GET(
      new Request("http://localhost/api/explore/refresh/due", {
        method: "GET",
        headers: { authorization: "Bearer vercel-secret" },
      }) as never,
    );

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.message).toHaveLength(500);
    expect(body.upstream_detail).toHaveLength(500);
    expect(body.upstream_message).toHaveLength(500);
    expect(textSpy).not.toHaveBeenCalled();
  });

  it("caps upstream plain-text errors", async () => {
    process.env.CRON_SECRET = "vercel-secret";
    delete process.env.EXPLORE_REFRESH_CRON_SECRET;
    global.fetch = vi.fn().mockResolvedValue(
      new Response("p".repeat(10000), { status: 500 }),
    );

    const res = await GET(
      new Request("http://localhost/api/explore/refresh/due", {
        method: "GET",
        headers: { authorization: "Bearer vercel-secret" },
      }) as never,
    );

    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.message).toHaveLength(500);
    expect(body.upstream_body).toHaveLength(500);
  });
});
