import { headers } from "next/headers";
import { notFound } from "next/navigation";
import ReportActions from "@/components/reports/ReportActions";
import ReportV11Detail from "@/components/reports/ReportV11Detail";
import type { FullReportData } from "@/lib/niche-finder/types";
import { loadCurrentProductUnlockState } from "@/lib/onboarding/unlock-state";

export const dynamic = "force-dynamic";

const APP_BASE_ENV_KEYS = [
  "WIDBY_APP_BASE_URL",
  "NEXT_PUBLIC_APP_URL",
  "NEXT_PUBLIC_SITE_URL",
] as const;

type HeaderReader = {
  get(name: string): string | null;
};

function normalizeAppBaseUrl(baseUrl: string) {
  const trimmed = baseUrl.trim().replace(/\/$/, "");
  if (!trimmed) return "";
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  return `https://${trimmed}`;
}

function getAppRouteUrl(path: string, headerStore: HeaderReader): string | null {
  for (const key of APP_BASE_ENV_KEYS) {
    const configured = process.env[key]?.trim();
    if (configured) return `${normalizeAppBaseUrl(configured)}${path}`;
  }

  const vercelUrl = process.env.VERCEL_URL?.trim();
  if (vercelUrl) return `${normalizeAppBaseUrl(vercelUrl)}${path}`;

  const host = headerStore.get("host")?.trim();
  if (!host) return null;

  try {
    const parsed = new URL(`http://${host}`);
    const hostname = parsed.hostname.replace(/^\[|\]$/g, "");
    const isLocalHost =
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname === "::1";
    if (!isLocalHost) return null;

    const proto = headerStore.get("x-forwarded-proto") === "https" ? "https" : "http";
    return `${proto}://${parsed.host}${path}`;
  } catch {
    return null;
  }
}

function isAbsoluteHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

async function loadReport(reportId: string): Promise<FullReportData | null> {
  const headerStore = await headers();
  const cookie = headerStore.get("cookie") ?? undefined;
  const url = getAppRouteUrl(
    `/api/agent/reports/${encodeURIComponent(reportId)}`,
    headerStore,
  );
  if (!url || !isAbsoluteHttpUrl(url)) return null;

  const response = await fetch(url, {
    cache: "no-store",
    ...(cookie ? { headers: { cookie } } : {}),
  });

  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`report detail: HTTP ${response.status}`);
  }

  const body = (await response.json()) as {
    status?: string;
    message?: string;
    report?: FullReportData;
  };

  if (body.status !== "success" || !body.report) {
    throw new Error(`report detail: ${body.message ?? "invalid response"}`);
  }

  return {
    ...body.report,
    metros: Array.isArray(body.report.metros) ? body.report.metros : [],
    resolved_weights: body.report.resolved_weights as Record<string, number> | null,
    meta: body.report.meta as Record<string, unknown> | null,
  };
}

export default async function ReportDetailPage({
  params,
}: {
  params: Promise<{ reportId: string }>;
}) {
  const { reportId } = await params;
  const report = await loadReport(reportId);
  if (!report) notFound();
  const nextStepContext = await loadCurrentProductUnlockState();

  return (
    <ReportV11Detail
      report={report}
      nextStepContext={nextStepContext}
      actions={<ReportActions report={report} enableArchiveDelete />}
    />
  );
}
