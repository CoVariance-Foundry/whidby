import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const CACHE_TTL_MS = 30_000;
const MAX_CACHE_ENTRIES = 200;
const UPSTREAM_TIMEOUT_MS = 4_500;

type CachedPlacesResponse = {
  expiresAt: number;
  data: unknown;
};

const placesSuggestCache = new Map<string, CachedPlacesResponse>();

function clampLimit(rawLimit: string | null): number {
  const parsed = Number(rawLimit ?? "8");
  if (!Number.isFinite(parsed)) return 8;
  return Math.min(Math.max(Math.trunc(parsed), 1), 20);
}

function cacheKey(query: string, limit: number): string {
  return `${query.trim().toLowerCase()}|${limit}`;
}

function getCachedValue(key: string): unknown | null {
  const now = Date.now();
  const hit = placesSuggestCache.get(key);
  if (!hit) return null;
  if (hit.expiresAt <= now) {
    placesSuggestCache.delete(key);
    return null;
  }
  return hit.data;
}

function setCachedValue(key: string, data: unknown): void {
  if (placesSuggestCache.size >= MAX_CACHE_ENTRIES) {
    let earliestExpiringKey: string | null = null;
    let earliestExpiresAt = Number.POSITIVE_INFINITY;

    for (const [cachedKey, cachedValue] of placesSuggestCache.entries()) {
      if (cachedValue.expiresAt < earliestExpiresAt) {
        earliestExpiringKey = cachedKey;
        earliestExpiresAt = cachedValue.expiresAt;
      }
    }

    if (earliestExpiringKey) placesSuggestCache.delete(earliestExpiringKey);
  }
  placesSuggestCache.set(key, { data, expiresAt: Date.now() + CACHE_TTL_MS });
}

export function __resetPlacesSuggestCacheForTests(): void {
  placesSuggestCache.clear();
}

export async function GET(req: NextRequest) {
  const startedAt = Date.now();
  const requestId = req.headers.get("x-request-id") || crypto.randomUUID();
  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q")?.trim() ?? "";
  const limit = clampLimit(searchParams.get("limit"));

  if (q.length < 2) {
    return NextResponse.json([]);
  }

  const key = cacheKey(q, limit);
  const cached = getCachedValue(key);
  if (cached !== null) {
    console.info(
      "[places-proxy] DONE request_id=%s cache_hit=true q=%s limit=%d duration_ms=%d",
      requestId,
      q,
      limit,
      Date.now() - startedAt,
    );
    return NextResponse.json(cached);
  }

  const upstreamParams = new URLSearchParams();
  upstreamParams.set("q", q);
  upstreamParams.set("limit", String(limit));
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);

  try {
    const upstream = await fetch(
      `${API_BASE}/api/places/suggest?${upstreamParams.toString()}`,
      {
        cache: "no-store",
        headers: { "x-request-id": requestId },
        signal: controller.signal,
      },
    );
    clearTimeout(timeout);
    if (!upstream.ok) {
      const upstreamBody = await upstream.text();
      return NextResponse.json(
        {
          status: "unavailable",
          request_id: requestId,
          upstream_status: upstream.status,
          upstream_body: upstreamBody.slice(0, 500),
        },
        { status: 502 },
      );
    }
    const data = await upstream.json();
    setCachedValue(key, data);
    console.info(
      "[places-proxy] DONE request_id=%s cache_hit=false q=%s limit=%d duration_ms=%d",
      requestId,
      q,
      limit,
      Date.now() - startedAt,
    );
    return NextResponse.json(data);
  } catch (err) {
    clearTimeout(timeout);
    const isAbort = err instanceof DOMException && err.name === "AbortError";
    return NextResponse.json(
      {
        status: "unavailable",
        request_id: requestId,
        error: isAbort
          ? `Places suggest upstream timed out after ${UPSTREAM_TIMEOUT_MS}ms`
          : err instanceof Error
            ? err.message
            : String(err),
      },
      { status: 502 },
    );
  }
}
