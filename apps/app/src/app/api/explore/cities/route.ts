import { NextRequest, NextResponse } from "next/server";
import {
  boundedUpstreamValue,
  unavailableFromUpstream,
} from "@/lib/api/upstream";

const DEFAULT_API_BASE = "http://localhost:8000";

function getApiBase() {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE;
}

function exploreCitiesUrl(req: NextRequest) {
  const upstreamUrl = new URL(`${getApiBase()}/api/explore/cities`);
  upstreamUrl.search = new URL(req.url).search;
  return upstreamUrl.toString();
}

export async function GET(req: NextRequest) {
  try {
    const upstream = await fetch(exploreCitiesUrl(req), {
      cache: "no-store",
    });

    if (!upstream.ok) {
      return unavailableFromUpstream(
        upstream,
        "Explore cities service is unavailable.",
      );
    }

    const data = await upstream.json();
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      {
        status: "unavailable",
        message: "Explore cities service is unavailable.",
        error: boundedUpstreamValue(
          err instanceof Error ? err.message : String(err),
        ),
      },
      { status: 502 },
    );
  }
}
