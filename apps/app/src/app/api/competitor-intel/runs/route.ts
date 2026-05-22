import { NextRequest, NextResponse } from "next/server";
import {
  EntitlementError,
  consumeReportQuotaUnits,
  refundReportQuotaUnits,
  resolveEntitlementContext,
} from "@/lib/account/entitlements";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";
import {
  proxyStrategyJsonResponse,
  proxyStrategyResponse,
  strategyUpstreamUnavailable,
} from "@/lib/strategies/api";

const COMPETITOR_INTEL_SCAN_COST = 2;

async function refundCompetitorIntelQuota(accountId: string): Promise<void> {
  try {
    await refundReportQuotaUnits(
      createAdminClient(),
      accountId,
      COMPETITOR_INTEL_SCAN_COST,
    );
  } catch (error) {
    console.warn(
      "[competitor-intel] quota refund failed",
      error instanceof Error ? error.message : String(error),
    );
  }
}

export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json(
      { status: "validation_error", message: "Invalid JSON body." },
      { status: 400 },
    );
  }

  let quotaConsumedForAccount: string | null = null;

  try {
    const supabase = await createClient();
    const { user, entitlement } = await resolveEntitlementContext(supabase);

    if (entitlement.plan_key === "free") {
      return NextResponse.json(
        {
          status: "upgrade_required",
          code: "competitor_intel_requires_paid_plan",
          message: "Competitor intel is available on Plus and Pro plans.",
          tier: entitlement.plan_key,
          monthly_report_limit: entitlement.monthly_report_limit,
        },
        { status: 403 },
      );
    }

    let quotaConsumed = 0;
    if (!entitlement.fresh_report_quota_exempt) {
      const consumed = await consumeReportQuotaUnits(
        supabase,
        entitlement.account_id,
        COMPETITOR_INTEL_SCAN_COST,
      );
      if (!consumed) {
        return NextResponse.json(
          {
            status: "quota_exceeded",
            code: "monthly_report_quota_exceeded",
            message: "You need 2 scans remaining to run competitor intel.",
            tier: entitlement.plan_key,
            monthly_report_limit: entitlement.monthly_report_limit,
            required_scans: COMPETITOR_INTEL_SCAN_COST,
          },
          { status: 429 },
        );
      }
      quotaConsumedForAccount = entitlement.account_id;
      quotaConsumed = COMPETITOR_INTEL_SCAN_COST;
    }

    const internalToken = process.env.STRATEGY_DISCOVERY_INTERNAL_TOKEN;
    const upstream = await proxyStrategyResponse("/api/competitor-intel/runs", {
      method: "POST",
      body: JSON.stringify({
        ...body,
        quota_consumed: quotaConsumed,
        account_id: entitlement.account_id,
        created_by_user_id: user.id,
      }),
      headers: internalToken ? { Authorization: `Bearer ${internalToken}` } : undefined,
    });

    if (!upstream.ok && quotaConsumedForAccount) {
      await refundCompetitorIntelQuota(quotaConsumedForAccount);
      quotaConsumedForAccount = null;
    }

    return proxyStrategyJsonResponse(upstream);
  } catch (err) {
    if (quotaConsumedForAccount) {
      await refundCompetitorIntelQuota(quotaConsumedForAccount);
    }

    if (err instanceof EntitlementError) {
      return NextResponse.json(
        { status: "error", code: err.code, message: err.message },
        { status: err.status },
      );
    }

    return strategyUpstreamUnavailable(
      err,
      "Competitor intel run service is unavailable.",
    );
  }
}
