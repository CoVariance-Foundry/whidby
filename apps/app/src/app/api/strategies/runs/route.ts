import { NextRequest, NextResponse } from "next/server";
import {
  EntitlementError,
  consumeReportQuota,
  refundReportQuota,
  resolveEntitlementContext,
} from "@/lib/account/entitlements";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";
import {
  proxyStrategyJsonResponse,
  proxyStrategyResponse,
  strategyUpstreamUnavailable,
} from "@/lib/strategies/api";
import type { StrategyRunRequest } from "@/lib/strategies/types";

const MAX_FRESH_TARGETS = 100;

function normalizedString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function keywordTokenCount(value: string): number {
  return value.match(/[a-z0-9]+/gi)?.length ?? 0;
}

function targetHasKeywordHijackShape(target: unknown): boolean {
  if (!target || typeof target !== "object") return false;
  const record = target as Record<string, unknown>;
  const keyword = normalizedString(record.primary_keyword);
  const cityOrMarket = Boolean(
    normalizedString(record.cbsa_code) ||
      normalizedString(record.city) ||
      normalizedString(record.city_id) ||
      normalizedString(record.reference_city_id),
  );
  const service = Boolean(
    normalizedString(record.service) ||
      normalizedString(record.niche_keyword) ||
      normalizedString(record.niche_normalized),
  );
  return Boolean(keyword && cityOrMarket && service && keywordTokenCount(keyword) >= 2);
}

function hasKeywordHijackTargetShape(body: StrategyRunRequest) {
  const keyword = normalizedString(body.primary_keyword);
  const city = normalizedString(body.city);
  const service = normalizedString(body.service);
  if (keyword && city && service && keywordTokenCount(keyword) >= 2) return true;
  if (Array.isArray(body.targets) && body.targets.length > 0) {
    return body.targets.every(targetHasKeywordHijackShape);
  }
  return false;
}

function isKeywordHijackFeasibilityMissing({
  mode,
  strategyId,
  body,
}: {
  mode: StrategyRunRequest["mode"];
  strategyId: string | undefined;
  body: StrategyRunRequest;
}) {
  return (
    mode === "fresh" &&
    strategyId === "keyword_hijack" &&
    (body.feasibility_preflight_passed !== true || !hasKeywordHijackTargetShape(body))
  );
}

async function refundFreshReportQuota(accountId: string): Promise<void> {
  try {
    await refundReportQuota(createAdminClient(), accountId);
  } catch (error) {
    console.warn(
      "[strategies] quota refund failed",
      error instanceof Error ? error.message : String(error),
    );
  }
}

export async function POST(req: NextRequest) {
  let body: StrategyRunRequest;
  try {
    body = (await req.json()) as StrategyRunRequest;
  } catch {
    return NextResponse.json(
      { status: "validation_error", message: "Invalid JSON body." },
      { status: 400 },
    );
  }

  let supabase: Awaited<ReturnType<typeof createClient>> | null = null;
  let quotaConsumedForAccount: string | null = null;

  try {
    supabase = await createClient();
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    const mode = body.mode ?? "cached";
    let quotaConsumed = 0;
    const strategy_id = body.strategy_id ?? body.lens_id;
    const bodyWithoutLensId = { ...body };
    delete bodyWithoutLensId.lens_id;
    delete bodyWithoutLensId.quota_consumed;

    if (mode === "fresh") {
      if (
        !entitlement.fresh_report_quota_exempt &&
        entitlement.monthly_report_limit <= 0
      ) {
        return NextResponse.json(
          {
            status: "tier_limit",
            code: "fresh_strategy_runs_not_included",
            message: "Your current plan can browse cached strategy results but cannot run fresh strategy discovery.",
            tier: entitlement.plan_key,
            monthly_report_limit: entitlement.monthly_report_limit,
          },
          { status: 403 },
        );
      }

      if (Array.isArray(body.targets) && body.targets.length > MAX_FRESH_TARGETS) {
        return NextResponse.json(
          {
            status: "validation_error",
            message: "Fresh strategy runs are limited to 100 target pairs.",
          },
          { status: 400 },
        );
      }

      if (
        isKeywordHijackFeasibilityMissing({
          mode,
          strategyId: strategy_id,
          body,
        })
      ) {
        return NextResponse.json(
          {
            status: "validation_error",
            code: "keyword_hijack_feasibility_required",
            message:
              "Keyword Hijack requires a feasibility preflight before fresh report spend.",
          },
          { status: 400 },
        );
      }

      if (!entitlement.fresh_report_quota_exempt) {
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
        quotaConsumed = 1;
      }
    }

    const internalToken = process.env.STRATEGY_DISCOVERY_INTERNAL_TOKEN;
    const upstream = await proxyStrategyResponse("/api/strategy-runs", {
      method: "POST",
      body: JSON.stringify({
        ...bodyWithoutLensId,
        ...(strategy_id ? { strategy_id } : {}),
        mode,
        quota_consumed: quotaConsumed,
        account_id: entitlement.account_id,
        created_by_user_id: user.id,
      }),
      headers: internalToken ? { Authorization: `Bearer ${internalToken}` } : undefined,
    });

    if (!upstream.ok && quotaConsumedForAccount) {
      await refundFreshReportQuota(quotaConsumedForAccount);
      quotaConsumedForAccount = null;
    }

    return proxyStrategyJsonResponse(upstream);
  } catch (err) {
    if (quotaConsumedForAccount && supabase) {
      await refundFreshReportQuota(quotaConsumedForAccount);
    }

    if (err instanceof EntitlementError) {
      return NextResponse.json(
        { status: "error", code: err.code, message: err.message },
        { status: err.status },
      );
    }

    return strategyUpstreamUnavailable(
      err,
      "Strategy run service is unavailable.",
    );
  }
}
