import { NextResponse } from "next/server";
import { EntitlementError, resolveEntitlementContext } from "@/lib/account/entitlements";
import { createClient } from "@/lib/supabase/server";
import {
  proxyStrategyJsonResponse,
  proxyStrategyResponse,
  strategyUpstreamUnavailable,
} from "@/lib/strategies/api";

export async function GET() {
  try {
    const supabase = await createClient();
    await resolveEntitlementContext(supabase);

    const upstream = await proxyStrategyResponse("/api/strategies", {
      method: "GET",
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
      "Strategy catalog service is unavailable.",
    );
  }
}
