import { NextRequest, NextResponse } from "next/server";
import { EntitlementError, resolveEntitlementContext } from "@/lib/account/entitlements";
import { createClient } from "@/lib/supabase/server";
import {
  proxyStrategyJsonResponse,
  proxyStrategyResponse,
  strategyUpstreamUnavailable,
} from "@/lib/strategies/api";

export async function GET(req: NextRequest) {
  try {
    const supabase = await createClient();
    const { entitlement } = await resolveEntitlementContext(supabase);

    if (entitlement.plan_key === "free") {
      return NextResponse.json({
        status: "upgrade_required",
        code: "competitor_intel_requires_paid_plan",
        message: "Competitor intel is available on Plus and Pro plans.",
        tier: entitlement.plan_key,
        monthly_report_limit: entitlement.monthly_report_limit,
      });
    }

    const searchParams = new URL(req.url).searchParams;
    searchParams.set("account_id", entitlement.account_id);
    const internalToken = process.env.STRATEGY_DISCOVERY_INTERNAL_TOKEN;
    const upstream = await proxyStrategyResponse(
      `/api/competitor-intel?${searchParams.toString()}`,
      {
        method: "GET",
        headers: internalToken ? { Authorization: `Bearer ${internalToken}` } : undefined,
      },
    );
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
      "Competitor intel service is unavailable.",
    );
  }
}
