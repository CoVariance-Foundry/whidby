import Link from "next/link";
import { headers } from "next/headers";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { Icon, I } from "@/lib/icons";
import type { TableRow } from "@/components/reports/ReportsTable";
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
  const rows = await loadReportRows();

  return (
    <div className="app density-roomy">
      <Sidebar active="reports" />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar
          crumbs={["Reports"]}
          actions={
            <Link href="/niche-finder" className="btn-primary" style={{ textDecoration: "none", display: "inline-flex" }}>
              <Icon d={I.plus} /> New report
            </Link>
          }
        />
        <main
          style={{
            padding: "24px 32px",
            maxWidth: 1280,
            margin: "0 auto",
            width: "100%",
            display: "flex",
            flexDirection: "column",
            gap: 20,
          }}
        >
          <header>
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
            <p
              style={{
                fontFamily: "var(--sans)",
                fontSize: 14,
                color: "var(--ink-2)",
                margin: "4px 0 0",
              }}
            >
              Every niche score you&apos;ve run, most recent first.
            </p>
          </header>
          <ReportsPageClient rows={rows} />
        </main>
      </div>
    </div>
  );
}
