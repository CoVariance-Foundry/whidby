import { NextRequest, NextResponse } from "next/server";
import {
  proxyStrategyJsonResponse,
  proxyStrategyResponse,
  strategyUpstreamUnavailable,
} from "@/lib/strategies/api";
import type { StrategyDiscoverRequest } from "@/lib/strategies/types";

export async function POST(req: NextRequest) {
  let body: StrategyDiscoverRequest;
  try {
    body = (await req.json()) as StrategyDiscoverRequest;
  } catch {
    return NextResponse.json(
      { status: "validation_error", message: "Invalid JSON body." },
      { status: 400 },
    );
  }

  try {
    const upstream = await proxyStrategyResponse("/api/discover", {
      method: "POST",
      body: JSON.stringify(body),
    });
    return proxyStrategyJsonResponse(upstream);
  } catch (err) {
    return strategyUpstreamUnavailable(
      err,
      "Strategy discovery service is unavailable.",
    );
  }
}
