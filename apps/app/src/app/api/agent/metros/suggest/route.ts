import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q") ?? "";
  const limit = searchParams.get("limit") ?? "";

  const upstreamParams = new URLSearchParams();
  upstreamParams.set("q", q);
  if (limit) upstreamParams.set("limit", limit);

  try {
    const upstream = await fetch(
      `${API_BASE}/api/metros/suggest?${upstreamParams.toString()}`,
      { cache: "no-store" },
    );
    if (!upstream.ok) {
      const upstreamBody = await upstream.text();
      return NextResponse.json(
        {
          status: "unavailable",
          upstream_status: upstream.status,
          upstream_body: upstreamBody.slice(0, 500),
        },
        { status: 502 },
      );
    }
    const data = await upstream.json();
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      {
        status: "unavailable",
        error: err instanceof Error ? err.message : String(err),
      },
      { status: 502 },
    );
  }
}
