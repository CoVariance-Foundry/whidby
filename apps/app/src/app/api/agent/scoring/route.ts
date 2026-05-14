import { NextRequest, NextResponse } from "next/server";
import {
  EntitlementError,
  consumeReportQuota,
  refundReportQuota,
  resolveEntitlementContext,
} from "@/lib/account/entitlements";
import { getServerFeatureFlag, captureServerEvent } from "@/lib/flags/server";
import { PRODUCT_FLAGS } from "@/lib/flags/product-flags";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";
import { createClient } from "@/lib/supabase/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const proxyStart = Date.now();
  let quotaConsumedForAccount: string | null = null;
  let supabaseForRefund: Awaited<ReturnType<typeof createClient>> | null = null;
  try {
    const supabase = await createClient();
    supabaseForRefund = supabase;
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    const flagProperties = {
      account_id: entitlement.account_id,
      tier: entitlement.plan_key,
      subscription_status: entitlement.subscription_status,
    };

    const freshReportsEnabled = await getServerFeatureFlag(
      PRODUCT_FLAGS.freshReportGenerationEnabled.key,
      PRODUCT_FLAGS.freshReportGenerationEnabled.defaultValue,
      user.id,
      flagProperties,
    );
    if (!freshReportsEnabled) {
      return NextResponse.json(
        {
          status: "disabled",
          code: "fresh_report_generation_disabled",
          message: "Fresh report generation is temporarily unavailable.",
        },
        { status: 503 },
      );
    }

    const quotaEnforcementEnabled = await getServerFeatureFlag(
      PRODUCT_FLAGS.reportQuotaEnforcementEnabled.key,
      PRODUCT_FLAGS.reportQuotaEnforcementEnabled.defaultValue,
      user.id,
      flagProperties,
    );

    if (quotaEnforcementEnabled) {
      if (entitlement.monthly_report_limit <= 0) {
        return NextResponse.json(
          {
            status: "tier_limit",
            code: "fresh_reports_not_included",
            message: "Your current plan can browse cached reports but cannot generate fresh reports.",
            tier: entitlement.plan_key,
            monthly_report_limit: entitlement.monthly_report_limit,
          },
          { status: 403 },
        );
      }

      const consumed = await consumeReportQuota(supabase, entitlement.account_id);
      if (!consumed) {
        return NextResponse.json(
          {
            status: "quota_exceeded",
            code: "monthly_report_quota_exceeded",
            message: "You have reached your monthly fresh report limit.",
            tier: entitlement.plan_key,
            monthly_report_limit: entitlement.monthly_report_limit,
          },
          { status: 429 },
        );
      }
      quotaConsumedForAccount = entitlement.account_id;
    }

    const body = await req.json();
    const validation = validateNicheQueryInput(body);
    if (!validation.ok) {
      if (quotaConsumedForAccount) {
        await refundReportQuota(supabase, quotaConsumedForAccount);
        quotaConsumedForAccount = null;
      }
      return NextResponse.json(
        { status: "validation_error", message: validation.message },
        { status: 400 },
      );
    }
    const dryRun = process.env.NEXT_PUBLIC_NICHE_DRY_RUN === "1";

    console.info(
      "[scoring-proxy] START city=%s service=%s dry_run=%s",
      body.city,
      body.service,
      dryRun,
    );

    const upstream = await fetch(`${API_BASE}/api/niches/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        niche: body.service.trim(),
        city: body.city.trim(),
        ...(typeof body.place_id === "string" && body.place_id.trim()
          ? { place_id: body.place_id.trim() }
          : {}),
        ...(typeof body.dataforseo_location_code === "number"
          ? { dataforseo_location_code: body.dataforseo_location_code }
          : {}),
        ...(typeof body.state === "string" && body.state.trim()
          ? { state: body.state.trim() }
          : {}),
        strategy_profile: body.strategy_profile ?? "balanced",
        dry_run: dryRun,
        owner_account_id: entitlement.account_id,
        created_by_user_id: user.id,
      }),
    });

    const proxyMs = Date.now() - proxyStart;

    if (!upstream.ok) {
      if (quotaConsumedForAccount) {
        await refundReportQuota(supabase, quotaConsumedForAccount);
        quotaConsumedForAccount = null;
      }
      const upstreamBody = await upstream.text();
      console.warn(
        "[scoring-proxy] FAIL upstream_status=%d proxy_ms=%d",
        upstream.status,
        proxyMs,
      );
      return NextResponse.json(
        {
          status: "unavailable",
          message: "Scoring engine did not return a result.",
          upstream_status: upstream.status,
          upstream_body: upstreamBody.slice(0, 2000),
        },
        { status: 502 },
      );
    }

    const data = await upstream.json();
    const totalMs = Date.now() - proxyStart;
    captureServerEvent(user.id, "fresh_report_generated", {
      account_id: entitlement.account_id,
      tier: entitlement.plan_key,
      report_id: data.report_id ?? null,
      opportunity_score: data.opportunity_score ?? null,
    });
    console.info(
      "[scoring-proxy] DONE report_id=%s opportunity=%d upstream_ms=%d total_ms=%d",
      data.report_id,
      data.opportunity_score,
      proxyMs,
      totalMs,
    );
    return NextResponse.json({
      query: {
        city: body.city.trim(),
        service: body.service.trim(),
        ...(typeof body.place_id === "string" && body.place_id.trim()
          ? { place_id: body.place_id.trim() }
          : {}),
        ...(typeof body.dataforseo_location_code === "number"
          ? { dataforseo_location_code: body.dataforseo_location_code }
          : {}),
        ...(typeof body.state === "string" && body.state.trim()
          ? { state: body.state.trim() }
          : {}),
      },
      score_result: {
        opportunity_score: data.opportunity_score,
        classification_label: data.classification_label,
      },
      report_id: data.report_id,
      entity_id: data.entity_id ?? null,
      snapshot_id: data.snapshot_id ?? null,
      persist_warning: data.persist_warning ?? null,
      account: {
        account_id: entitlement.account_id,
        tier: entitlement.plan_key,
        monthly_report_limit: entitlement.monthly_report_limit,
      },
      status: "success",
    });
  } catch (err) {
    if (quotaConsumedForAccount && supabaseForRefund) {
      await refundReportQuota(supabaseForRefund, quotaConsumedForAccount);
    }
    const proxyMs = Date.now() - proxyStart;
    if (err instanceof EntitlementError) {
      return NextResponse.json(
        {
          status: "entitlement_error",
          code: err.code,
          message: err.message,
        },
        { status: err.status },
      );
    }
    console.error(
      "[scoring-proxy] ERROR proxy_ms=%d error=%s",
      proxyMs,
      err instanceof Error ? err.message : String(err),
    );
    return NextResponse.json(
      {
        status: "unavailable",
        message: "Failed to process scoring request.",
        error: err instanceof Error ? err.message : String(err),
      },
      { status: 502 },
    );
  }
}
