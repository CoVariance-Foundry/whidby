import { headers } from "next/headers";
import {
  fromSearchParams,
  normalizeExploreData,
  toExploreSearchParams,
  type BackendExploreData,
  type ExploreQueryParams,
} from "./normalize-explore-data";
import type { ExploreData } from "./types";

export { fromSearchParams, toExploreSearchParams, type ExploreQueryParams };

interface LoadExploreDataOptions {
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

export async function loadExploreData(
  params: ExploreQueryParams = {},
  options: LoadExploreDataOptions = {},
): Promise<ExploreData> {
  const query = toExploreSearchParams(params);
  const queryString = query.toString();
  const path = `/api/explore/cities${queryString ? `?${queryString}` : ""}`;
  const url = await getAppRouteUrl(path, options.app_base_url);
  const cookie = await getIncomingCookieHeader(Boolean(options.app_base_url));

  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
      ...(cookie ? { headers: { cookie } } : {}),
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "request failed";
    throw new Error(`loadExploreData explore cities: ${detail}`);
  }

  if (!response.ok) {
    throw new Error(`loadExploreData explore cities: HTTP ${response.status}`);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    throw new Error("loadExploreData explore cities: expected JSON response");
  }

  return normalizeExploreData((await response.json()) as BackendExploreData);
}
