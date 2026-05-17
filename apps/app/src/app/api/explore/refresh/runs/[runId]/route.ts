import { NextRequest, NextResponse } from "next/server";

const DEFAULT_API_BASE = "http://localhost:8000";
const MAX_UPSTREAM_ERROR_CHARS = 500;
const MAX_UPSTREAM_BODY_CHARS = 4096;

type RouteContext = {
  params: Promise<{ runId: string }>;
};

function getApiBase() {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE;
}

function boundedUpstreamValue(value: unknown): string | undefined {
  if (value === undefined || value === null) return undefined;
  if (typeof value === "string") return value.slice(0, MAX_UPSTREAM_ERROR_CHARS);
  try {
    return JSON.stringify(value).slice(0, MAX_UPSTREAM_ERROR_CHARS);
  } catch {
    return String(value).slice(0, MAX_UPSTREAM_ERROR_CHARS);
  }
}

async function readBoundedResponseBody(upstream: Response) {
  if (!upstream.body) return "";

  const reader = upstream.body.getReader();
  const decoder = new TextDecoder();
  let text = "";
  let reachedLimit = false;

  try {
    while (text.length < MAX_UPSTREAM_BODY_CHARS) {
      const { done, value } = await reader.read();
      if (done) break;
      const remaining = MAX_UPSTREAM_BODY_CHARS - text.length;
      const chunk = value.byteLength > remaining ? value.subarray(0, remaining) : value;
      text += decoder.decode(chunk, { stream: true });
      if (text.length >= MAX_UPSTREAM_BODY_CHARS) {
        text = text.slice(0, MAX_UPSTREAM_BODY_CHARS);
        reachedLimit = true;
      }
      if (value.byteLength > remaining || reachedLimit) {
        await reader.cancel();
        break;
      }
    }
    if (!reachedLimit && text.length < MAX_UPSTREAM_BODY_CHARS) {
      text += decoder.decode();
    }
  } finally {
    reader.releaseLock();
  }

  return text.slice(0, MAX_UPSTREAM_BODY_CHARS);
}

async function unavailableFromUpstream(
  upstream: Response,
  fallbackMessage: string,
) {
  const responseBody: Record<string, unknown> = {
    status: "unavailable",
    message: fallbackMessage,
    upstream_status: upstream.status,
  };

  const text = await readBoundedResponseBody(upstream);
  if (!text) {
    return NextResponse.json(responseBody, { status: 502 });
  }

  try {
    const parsed = JSON.parse(text) as {
      detail?: unknown;
      message?: unknown;
      error?: unknown;
    };
    const upstreamMessage = boundedUpstreamValue(
      parsed.message ?? parsed.detail ?? parsed.error,
    );
    if (upstreamMessage) responseBody.message = upstreamMessage;
    if (parsed.detail !== undefined) {
      responseBody.upstream_detail = boundedUpstreamValue(parsed.detail);
    }
    if (parsed.message !== undefined) {
      responseBody.upstream_message = boundedUpstreamValue(parsed.message);
    }
    if (parsed.error !== undefined) {
      responseBody.upstream_error = boundedUpstreamValue(parsed.error);
    }
  } catch {
    responseBody.message = text.slice(0, MAX_UPSTREAM_ERROR_CHARS);
    responseBody.upstream_body = text.slice(0, MAX_UPSTREAM_ERROR_CHARS);
  }

  return NextResponse.json(responseBody, { status: 502 });
}

export async function GET(_req: NextRequest, { params }: RouteContext) {
  const { runId } = await params;

  try {
    const upstream = await fetch(
      `${getApiBase()}/api/explore/refresh/runs/${encodeURIComponent(runId)}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      },
    );

    if (!upstream.ok) {
      return unavailableFromUpstream(
        upstream,
        "Explore refresh status service is unavailable.",
      );
    }

    const data = await upstream.json();
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      {
        status: "unavailable",
        message: "Explore refresh status service is unavailable.",
        error: boundedUpstreamValue(
          err instanceof Error ? err.message : String(err),
        ),
      },
      { status: 502 },
    );
  }
}
