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

const DEFAULT_LOCAL_API_BASE_URL = "http://localhost:8000";

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

function normalizeApiBaseUrl(baseUrl: string) {
  const trimmed = baseUrl.trim().replace(/\/$/, "");
  if (!trimmed) return "";
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  return `https://${trimmed}`;
}

function isProductionRuntime() {
  return (
    process.env.NODE_ENV === "production" ||
    process.env.VERCEL_ENV === "production"
  );
}

function getApiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) return normalizeApiBaseUrl(configured);
  if (!isProductionRuntime()) return DEFAULT_LOCAL_API_BASE_URL;
  throw new Error(
    "loadExploreData explore cities: NEXT_PUBLIC_API_URL is required in production and must point to the API/Render service",
  );
}

async function getAppOrigin(injectedBaseUrl?: string) {
  const injected = injectedBaseUrl ? normalizeAppBaseUrl(injectedBaseUrl) : "";
  if (injected) return new URL(injected).origin;

  for (const key of APP_BASE_ENV_KEYS) {
    const configured = process.env[key]?.trim();
    if (configured) return new URL(normalizeAppBaseUrl(configured)).origin;
  }

  const vercelUrl = process.env.VERCEL_URL?.trim();
  if (vercelUrl) return new URL(normalizeAppBaseUrl(vercelUrl)).origin;

  if (typeof window !== "undefined") return undefined;

  const headerStore = await headers();
  const host = headerStore.get("x-forwarded-host") ?? headerStore.get("host");
  if (!host) return undefined;
  const proto = headerStore.get("x-forwarded-proto") ?? "http";
  return new URL(`${proto}://${host}`).origin;
}

async function getExploreCitiesUrl(path: string, injectedAppBaseUrl?: string) {
  if (typeof window !== "undefined") return path;

  const apiBaseUrl = getApiBaseUrl();
  const apiOrigin = new URL(apiBaseUrl).origin;
  const appOrigin = await getAppOrigin(injectedAppBaseUrl);
  if (appOrigin && apiOrigin === appOrigin) {
    throw new Error(
      "loadExploreData explore cities: NEXT_PUBLIC_API_URL must point to the API/Render service, not the app origin",
    );
  }

  return `${apiBaseUrl}${path}`;
}

export async function loadExploreData(
  params: ExploreQueryParams = {},
  options: LoadExploreDataOptions = {},
): Promise<ExploreData> {
  const query = toExploreSearchParams(params);
  const queryString = query.toString();
  const path = `/api/explore/cities${queryString ? `?${queryString}` : ""}`;
  const url = await getExploreCitiesUrl(path, options.app_base_url);

  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
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
