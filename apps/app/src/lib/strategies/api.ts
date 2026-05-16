import { NextResponse } from "next/server";

export const DEFAULT_STRATEGY_API_BASE = "http://localhost:8000";
const MAX_UPSTREAM_ERROR_CHARS = 2000;

export function getStrategyApiBase() {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_STRATEGY_API_BASE;
}

export async function proxyStrategyResponse(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  return fetch(`${getStrategyApiBase()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers as Record<string, string> | undefined),
    },
    cache: "no-store",
  });
}

export async function proxyStrategyJsonResponse(upstream: Response) {
  const text = await upstream.text();
  let body: unknown = {};
  if (text) {
    try {
      body = JSON.parse(text) as unknown;
    } catch {
      body = { status: "upstream_response", upstream_body: text.slice(0, MAX_UPSTREAM_ERROR_CHARS) };
    }
  }

  return NextResponse.json(body, { status: upstream.status });
}

export function strategyUpstreamUnavailable(
  err: unknown,
  message: string,
) {
  return NextResponse.json(
    {
      status: "unavailable",
      message,
      error: err instanceof Error ? err.message.slice(0, 500) : String(err).slice(0, 500),
    },
    { status: 502 },
  );
}
