import { headers } from "next/headers";
import type { User } from "@supabase/supabase-js";
import {
  EntitlementError,
  type AccountEntitlement,
  type PlanKey,
  resolveEntitlementContext,
} from "@/lib/account/entitlements";
import { type AccountSummary, loadAccountSummary } from "@/lib/account/summary";
import type { ActivityItem, RecommendedItem, StatCard } from "@/lib/home/types";
import { loadProductUnlockState } from "@/lib/onboarding/unlock-state";
import { resolveOnboardingSegmentRoute } from "@/lib/onboarding/segment-routing";
import type { OnboardingNextRoute } from "@/lib/onboarding/types";
import { loadStrategyCatalog } from "@/lib/strategies/catalog";
import {
  getRunnableStrategyPathNodes,
  isUserFacingStrategyId,
  sortByStrategyPathOrder,
} from "@/lib/strategies/path-registry";
import type { RunnableStrategyPathId } from "@/lib/strategies/path-registry";
import type { StrategyCatalogEntry, StrategyCatalogResponse } from "@/lib/strategies/types";
import { createClient } from "@/lib/supabase/server";

type LaunchSafeStrategyId = RunnableStrategyPathId;
type DashboardNextRoute = OnboardingNextRoute;

interface DashboardError {
  message: string;
  code?: string;
  status?: number;
}

interface DashboardAccountReady {
  status: "ready";
  error: null;
  summary: AccountSummary;
  entitlement: DashboardEntitlementSummary;
  can_run_fresh_reports: boolean;
}

interface DashboardAccountError {
  status: "error";
  error: DashboardError;
  blocking: boolean;
  summary: null;
  entitlement: DashboardEntitlementSummary | null;
  can_run_fresh_reports: boolean;
}

type DashboardAccountState = DashboardAccountReady | DashboardAccountError;

interface DashboardEntitlementSummary {
  account_id: string;
  plan_key: PlanKey;
  fresh_report_quota_exempt: boolean;
}

interface OnboardingProfileRow {
  id: string;
  user_id?: string | null;
  account_id?: string | null;
  intent?: string | null;
  recommended_strategy_id?: string | null;
  available_strategy_ids?: string[] | null;
  next_route?: string | null;
  status?: string | null;
  [key: string]: unknown;
}

interface OnboardingTargetRow {
  id: string;
  onboarding_profile_id?: string | null;
  strategy_id?: string | null;
  niche_keyword?: string | null;
  geo_scope?: string | null;
  city?: string | null;
  state?: string | null;
  resolved_label?: string | null;
  updated_at?: string | null;
  [key: string]: unknown;
}

interface DashboardOnboardingContext {
  profile: OnboardingProfileRow | null;
  target: OnboardingTargetRow | null;
  starter_strategy_id: LaunchSafeStrategyId;
  shortcut_strategy_ids: LaunchSafeStrategyId[];
  next_route: DashboardNextRoute;
  has_completed_scan: boolean;
  has_ranked_site_declaration: boolean;
  error: DashboardError | null;
}

interface DashboardStrategyContext {
  catalog: StrategyCatalogResponse;
  starter: StrategyCatalogEntry;
  shortcuts: StrategyCatalogEntry[];
}

type ReportsDashboardBody = {
  status?: string;
  message?: string;
  dashboard?: Pick<DashboardData, "stats" | "recent" | "recommended" | "stat_cards">;
};

export interface DashboardData {
  stats: {
    total_reports: number;
    avg_score: number;
    watchlist: number; // placeholder: 0 until saved-searches ships
    niches_scored: number; // same as total_reports in Foundation; diverges later
  };
  recent: ActivityItem[];
  recommended: RecommendedItem[];
  stat_cards: StatCard[];
  account: DashboardAccountState;
  onboarding: DashboardOnboardingContext;
  strategies: DashboardStrategyContext;
  report_error: DashboardError | null;
  multi_market_available: boolean;
}

interface LoadDashboardOptions {
  app_base_url?: string;
  multi_market_available?: boolean;
}

const APP_BASE_ENV_KEYS = [
  "WIDBY_APP_BASE_URL",
  "NEXT_PUBLIC_APP_URL",
  "NEXT_PUBLIC_SITE_URL",
] as const;
const STARTER_FALLBACK = "easy_win" satisfies LaunchSafeStrategyId;
const LAUNCH_SAFE_STRATEGY_IDS = getRunnableStrategyPathNodes().map(
  (node) => node.strategy_id,
) satisfies LaunchSafeStrategyId[];
const LAUNCH_SAFE_STRATEGY_SET = new Set<string>(LAUNCH_SAFE_STRATEGY_IDS);
// Phase 2 route-gates Multi-market only. This branch already includes /agency,
// so production defaults to enabled while tests can still cover the disabled card.
const DEFAULT_MULTI_MARKET_AVAILABLE = true;
const FALLBACK_STRATEGY_ENTRIES = Object.fromEntries(
  getRunnableStrategyPathNodes().map((strategy) => [
    strategy.strategy_id,
    {
      strategy_id: strategy.strategy_id,
      name: strategy.name,
      description: strategy.description,
      status: strategy.status,
      input_shape: strategy.input_shape,
      path_role: strategy.path_role,
      path_order: strategy.path_order,
      is_visible: strategy.is_visible,
      is_runnable: strategy.is_runnable,
      unlock_requirement: strategy.unlock_requirement,
    },
  ]),
) as Record<LaunchSafeStrategyId, StrategyCatalogEntry>;
function normalizeAppBaseUrl(baseUrl: string) {
  const trimmed = baseUrl.trim().replace(/\/$/, "");
  if (!trimmed) return "";
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  return `https://${trimmed}`;
}

async function getAppRouteUrl(path: string, injectedBaseUrl?: string) {
  const injected = injectedBaseUrl ? normalizeAppBaseUrl(injectedBaseUrl) : "";
  if (injected) return `${injected}${path}`;

  for (const key of APP_BASE_ENV_KEYS) {
    const configured = process.env[key]?.trim();
    if (configured) return `${normalizeAppBaseUrl(configured)}${path}`;
  }

  const vercelUrl = process.env.VERCEL_URL?.trim();
  if (vercelUrl) return `${normalizeAppBaseUrl(vercelUrl)}${path}`;

  if (typeof window !== "undefined") return path;

  const headerStore = await headers();
  const host = headerStore.get("x-forwarded-host") ?? headerStore.get("host");
  if (!host) return path;
  const proto = headerStore.get("x-forwarded-proto") ?? "http";
  return `${proto}://${host}${path}`;
}

async function getIncomingCookieHeader(skipRequestHeaders = false) {
  if (skipRequestHeaders || typeof window !== "undefined") return undefined;
  const headerStore = await headers();
  return headerStore.get("cookie") ?? undefined;
}

function emptyReportsDashboard() {
  return {
    stats: {
      total_reports: 0,
      avg_score: 0,
      watchlist: 0,
      niches_scored: 0,
    },
    recent: [] satisfies ActivityItem[],
    recommended: [] satisfies RecommendedItem[],
    stat_cards: [
      { label: "Niches scored", value: "0" },
      { label: "Watchlist", value: "0" },
      { label: "Avg score", value: "0" },
      { label: "Reports", value: "0" },
    ] satisfies StatCard[],
  };
}

function errorFromUnknown(error: unknown, fallbackMessage: string): DashboardError {
  if (error instanceof EntitlementError) {
    return {
      message: error.message,
      code: error.code,
      status: error.status,
    };
  }

  if (error instanceof Error) {
    return { message: error.message };
  }

  return { message: fallbackMessage };
}

function normalizeLaunchSafeStrategyId(value: unknown): LaunchSafeStrategyId | null {
  if (typeof value !== "string") return null;
  return LAUNCH_SAFE_STRATEGY_SET.has(value) ? (value as LaunchSafeStrategyId) : null;
}

function normalizeShortcutStrategyIds(
  starter: LaunchSafeStrategyId,
  values: unknown,
): LaunchSafeStrategyId[] {
  const shortcuts = Array.isArray(values)
    ? values
        .map((value) => normalizeLaunchSafeStrategyId(value))
        .filter((value): value is LaunchSafeStrategyId => Boolean(value))
    : [];
  const unique = Array.from(new Set([starter, ...shortcuts]));
  return unique.length ? unique : [STARTER_FALLBACK];
}

function filterLaunchCatalog(catalog: StrategyCatalogResponse): StrategyCatalogResponse {
  const strategies = sortByStrategyPathOrder(
    catalog.strategies.filter((strategy) => isUserFacingStrategyId(strategy.strategy_id)),
  );
  return {
    ...catalog,
    strategies,
  };
}

function strategyEntryById(
  catalog: StrategyCatalogResponse,
  strategyId: LaunchSafeStrategyId,
): StrategyCatalogEntry {
  return (
    catalog.strategies.find((strategy) => strategy.strategy_id === strategyId) ?? {
      ...FALLBACK_STRATEGY_ENTRIES[strategyId],
    }
  );
}

function canRunFreshReports(summary: AccountSummary, entitlement: AccountEntitlement) {
  if (entitlement.fresh_report_quota_exempt) return true;
  if (entitlement.plan_key === "free") return false;
  return summary.fresh_reports_remaining > 0;
}

function canRunFreshReportsWithoutSummary(entitlement: AccountEntitlement) {
  return entitlement.fresh_report_quota_exempt || entitlement.plan_key !== "free";
}

function summarizeEntitlement(entitlement: AccountEntitlement): DashboardEntitlementSummary {
  return {
    account_id: entitlement.account_id,
    plan_key: entitlement.plan_key,
    fresh_report_quota_exempt: entitlement.fresh_report_quota_exempt,
  };
}

function resolveMultiMarketAvailability(options: LoadDashboardOptions) {
  return options.multi_market_available ?? DEFAULT_MULTI_MARKET_AVAILABLE;
}

async function loadOnboardingContext(
  supabase: Awaited<ReturnType<typeof createClient>>,
  user: User,
): Promise<{
  profile: OnboardingProfileRow | null;
  target: OnboardingTargetRow | null;
  error: DashboardError | null;
}> {
  const { data: profile, error: profileError } = await supabase
    .from("onboarding_profiles")
    .select("*")
    .eq("user_id", user.id)
    .maybeSingle();

  if (profileError) {
    return {
      profile: null,
      target: null,
      error: { message: profileError.message },
    };
  }

  if (!profile) {
    return { profile: null, target: null, error: null };
  }

  const { data: target, error: targetError } = await supabase
    .from("onboarding_targets")
    .select("*")
    .eq("onboarding_profile_id", (profile as OnboardingProfileRow).id)
    .order("updated_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (targetError) {
    return {
      profile: profile as OnboardingProfileRow,
      target: null,
      error: { message: targetError.message },
    };
  }

  return {
    profile: profile as OnboardingProfileRow,
    target: (target as OnboardingTargetRow | null) ?? null,
    error: null,
  };
}

async function loadReportsDashboard(
  options: LoadDashboardOptions,
): Promise<{
  reports: Pick<DashboardData, "stats" | "recent" | "recommended" | "stat_cards">;
  report_error: DashboardError | null;
}> {
  const fallback = emptyReportsDashboard();
  const url = await getAppRouteUrl(
    "/api/agent/reports?view=dashboard&limit=10",
    options.app_base_url,
  );
  const cookie = await getIncomingCookieHeader(Boolean(options.app_base_url));

  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
      ...(cookie ? { headers: { cookie } } : {}),
    });
  } catch (error) {
    return {
      reports: fallback,
      report_error: errorFromUnknown(error, "Reports request failed."),
    };
  }

  if (!response.ok) {
    return {
      reports: fallback,
      report_error: { message: `Reports request failed with HTTP ${response.status}.` },
    };
  }

  let body: ReportsDashboardBody;
  try {
    body = (await response.json()) as ReportsDashboardBody;
  } catch {
    return {
      reports: fallback,
      report_error: { message: "Reports response was invalid JSON." },
    };
  }

  if (body.status !== "success" || !body.dashboard) {
    return {
      reports: fallback,
      report_error: { message: body.message ?? "Reports response was invalid." },
    };
  }

  return { reports: body.dashboard, report_error: null };
}

export async function loadDashboard(
  options: LoadDashboardOptions = {},
): Promise<DashboardData> {
  const catalog = filterLaunchCatalog(await loadStrategyCatalog());

  let account: DashboardAccountState;
  let canLoadReports = false;
  let hasCompletedScan = false;
  let hasRankedSiteDeclaration = false;
  let onboardingRows: Awaited<ReturnType<typeof loadOnboardingContext>> = {
    profile: null,
    target: null,
    error: null,
  };

  try {
    const supabase = await createClient();
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    onboardingRows = await loadOnboardingContext(supabase, user);
    const unlockState = await loadProductUnlockState(supabase, entitlement.account_id);
    hasCompletedScan = unlockState.has_completed_scan;
    hasRankedSiteDeclaration = unlockState.has_ranked_site_declaration;
    canLoadReports = true;

    try {
      const summary = await loadAccountSummary({ supabase, user, entitlement });
      account = {
        status: "ready",
        error: null,
        summary,
        entitlement: summarizeEntitlement(entitlement),
        can_run_fresh_reports: canRunFreshReports(summary, entitlement),
      };
    } catch (error) {
      account = {
        status: "error",
        error: errorFromUnknown(error, "Account summary is unavailable."),
        blocking: false,
        summary: null,
        entitlement: summarizeEntitlement(entitlement),
        can_run_fresh_reports: canRunFreshReportsWithoutSummary(entitlement),
      };
    }
  } catch (error) {
    account = {
      status: "error",
      error: errorFromUnknown(error, "Account context is unavailable."),
      blocking: true,
      summary: null,
      entitlement: null,
      can_run_fresh_reports: false,
    };
  }

  const starter =
    normalizeLaunchSafeStrategyId(onboardingRows.profile?.recommended_strategy_id) ??
    STARTER_FALLBACK;
  const shortcutIds = normalizeShortcutStrategyIds(
    starter,
    onboardingRows.profile?.available_strategy_ids,
  );
  const strategyContext: DashboardStrategyContext = {
    catalog,
    starter: strategyEntryById(catalog, starter),
    shortcuts: shortcutIds.map((strategyId) => strategyEntryById(catalog, strategyId)),
  };
  const { reports, report_error } =
    canLoadReports
      ? await loadReportsDashboard(options)
      : { reports: emptyReportsDashboard(), report_error: null };
  const segmentRoute = resolveOnboardingSegmentRoute({
    profile: onboardingRows.profile,
    report_history: {
      completed_report_count: hasCompletedScan ? 1 : 0,
      has_ranked_site_declaration: hasRankedSiteDeclaration,
    },
  });
  const onboarding: DashboardOnboardingContext = {
    profile: onboardingRows.profile,
    target: onboardingRows.target,
    starter_strategy_id: starter,
    shortcut_strategy_ids: shortcutIds,
    next_route: segmentRoute.route,
    has_completed_scan: hasCompletedScan,
    has_ranked_site_declaration: hasRankedSiteDeclaration,
    error: onboardingRows.error,
  };

  return {
    ...reports,
    account,
    onboarding,
    strategies: strategyContext,
    report_error,
    multi_market_available: resolveMultiMarketAvailability(options),
  };
}
