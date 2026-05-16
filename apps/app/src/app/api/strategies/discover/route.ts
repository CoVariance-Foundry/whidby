import { NextRequest, NextResponse } from "next/server";
import { EntitlementError, resolveEntitlementContext } from "@/lib/account/entitlements";
import { createClient } from "@/lib/supabase/server";
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
    const supabase = await createClient();
    await resolveEntitlementContext(supabase);

    const internalToken = process.env.STRATEGY_DISCOVERY_INTERNAL_TOKEN;
    const upstream = await proxyStrategyResponse("/api/discover", {
      method: "POST",
      body: JSON.stringify(body),
      headers: internalToken ? { Authorization: `Bearer ${internalToken}` } : undefined,
    });
    return proxyStrategyJsonResponse(upstream);
  } catch (err) {
    if (err instanceof EntitlementError) {
      return NextResponse.json(
        { status: "error", code: err.code, message: err.message },
        { status: err.status },
      );
    }

    return strategyUpstreamUnavailable(
      err,
      "Strategy discovery service is unavailable.",
    );
  }
}
