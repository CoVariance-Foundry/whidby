import { headers } from "next/headers";
import type { ActivityItem } from "@/components/home/RecentActivityFeed";
import type { RecommendedItem } from "@/components/home/RecommendedMetros";
import type { StatCard } from "@/components/home/StatCardRow";

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
}

interface LoadDashboardOptions {
  app_base_url?: string;
}

const APP_BASE_ENV_KEYS = [
  "WIDBY_APP_BASE_URL",
  "NEXT_PUBLIC_APP_URL",
  "NEXT_PUBLIC_SITE_URL",
] as const;

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

export async function loadDashboard(
  options: LoadDashboardOptions = {},
): Promise<DashboardData> {
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
    const detail = error instanceof Error ? error.message : "request failed";
    throw new Error(`loadDashboard: ${detail}`);
  }

  if (!response.ok) {
    throw new Error(`loadDashboard: HTTP ${response.status}`);
  }

  const body = (await response.json()) as {
    status?: string;
    message?: string;
    dashboard?: DashboardData;
  };

  if (body.status !== "success" || !body.dashboard) {
    throw new Error(`loadDashboard: ${body.message ?? "invalid response"}`);
  }

  return body.dashboard;
}
