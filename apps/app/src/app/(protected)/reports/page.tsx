import Link from "next/link";
import { headers } from "next/headers";
import { Icon, I } from "@/lib/icons";
import type { TableRow } from "@/components/reports/ReportsTable";
import { loadCurrentProductUnlockState } from "@/lib/onboarding/unlock-state";
import ReportsPageClient from "./ReportsPageClient";

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

function getAppRouteUrl(path: string, headerStore: HeaderReader) {
  for (const key of APP_BASE_ENV_KEYS) {
    const configured = process.env[key]?.trim();
    if (configured) return `${normalizeAppBaseUrl(configured)}${path}`;
  }

  const vercelUrl = process.env.VERCEL_URL?.trim();
  if (vercelUrl) return `${normalizeAppBaseUrl(vercelUrl)}${path}`;

  const host = headerStore.get("x-forwarded-host") ?? headerStore.get("host");
  if (!host) return path;
  const proto = headerStore.get("x-forwarded-proto") ?? "http";
  return `${proto}://${host}${path}`;
}

async function loadReportRows(): Promise<TableRow[]> {
  const headerStore = await headers();
  const cookie = headerStore.get("cookie") ?? undefined;
  const url = getAppRouteUrl("/api/agent/reports?limit=50", headerStore);
  const response = await fetch(url, {
    cache: "no-store",
    ...(cookie ? { headers: { cookie } } : {}),
  });

  if (!response.ok) {
    throw new Error(`reports list: HTTP ${response.status}`);
  }

  const body = (await response.json()) as {
    status?: string;
    message?: string;
    reports?: TableRow[];
  };

  if (body.status !== "success" || !Array.isArray(body.reports)) {
    throw new Error(`reports list: ${body.message ?? "invalid response"}`);
  }

  return body.reports;
}

export default async function ReportsPage() {
  const [rows, nextStepContext] = await Promise.all([
    loadReportRows(),
    loadCurrentProductUnlockState(),
  ]);

  return (
    <main
      className="page"
      style={{
        maxWidth: 1280,
        margin: "0 auto",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: 18,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1
            style={{
              fontFamily: "var(--serif)",
              fontSize: 28,
              fontWeight: 600,
              color: "var(--ink)",
              margin: 0,
            }}
          >
            Reports
          </h1>
          <div
            style={{
              fontFamily: "var(--sans)",
              fontSize: 11,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--ink-3)",
              marginTop: 4,
            }}
          >
            History
          </div>
          <p
            style={{
              fontFamily: "var(--sans)",
              fontSize: 14,
              color: "var(--ink-2)",
              margin: "4px 0 0",
              maxWidth: 660,
            }}
          >
            Every scan you run produces a report. Come back anytime; saved reports do not cost additional scans to revisit.
          </p>
        </div>
        <Link href="/niche-finder" className="btn-primary" style={{ textDecoration: "none" }}>
          <Icon d={I.plus} /> New report
        </Link>
      </header>
      <ReportsPageClient rows={rows} nextStepContext={nextStepContext} />
    </main>
  );
}
