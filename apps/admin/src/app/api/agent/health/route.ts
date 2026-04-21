import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/health`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
    const text = await res.text();
    return NextResponse.json(
      {
        status: res.ok ? "ok" : "unavailable",
        upstream: res.ok ? "ok" : "error",
        upstream_status: res.status,
        upstream_body: text.slice(0, 500),
        api_base: API_BASE,
      },
      { status: res.ok ? 200 : 502 },
    );
  } catch (err) {
    return NextResponse.json(
      {
        status: "unavailable",
        upstream: "unreachable",
        error: err instanceof Error ? err.message : String(err),
        api_base: API_BASE,
      },
      { status: 502 },
    );
  }
}
