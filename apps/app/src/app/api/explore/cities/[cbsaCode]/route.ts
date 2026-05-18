import { NextRequest, NextResponse } from "next/server";
import {
  boundedUpstreamValue,
  readJsonOrNull,
  unavailableFromUpstream,
} from "@/lib/api/upstream";

const DEFAULT_API_BASE = "http://localhost:8000";

type RouteContext = {
  params: Promise<{ cbsaCode: string }> | { cbsaCode: string };
};

function getApiBase() {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE;
}

export async function GET(_req: NextRequest, context: RouteContext) {
  try {
    const { cbsaCode } = await context.params;
    const upstream = await fetch(
      `${getApiBase()}/api/explore/cities/${encodeURIComponent(cbsaCode)}`,
      { cache: "no-store" },
    );

    if (upstream.status === 404) {
      const data = await readJsonOrNull(upstream);
      return NextResponse.json(data ?? { detail: "Not found" }, { status: 404 });
    }

    if (!upstream.ok) {
      return unavailableFromUpstream(
        upstream,
        "Explore city detail service is unavailable.",
      );
    }

    const data = await upstream.json();
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      {
        status: "unavailable",
        message: "Explore city detail service is unavailable.",
        error: boundedUpstreamValue(
          err instanceof Error ? err.message : String(err),
        ),
      },
      { status: 502 },
    );
  }
}
