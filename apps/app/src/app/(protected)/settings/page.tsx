import { EntitlementError, resolveEntitlementContext } from "@/lib/account/entitlements";
import { loadAccountSummary } from "@/lib/account/summary";
import { createClient } from "@/lib/supabase/server";
import { headers } from "next/headers";
import AccountSettingsClient from "./AccountSettingsClient";
import type { ProfileSummary, SavedReportPreview } from "./AccountSettingsClient";

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

function firstMetadataString(
  metadata: Record<string, unknown> | null | undefined,
  keys: string[],
): string | null {
  for (const key of keys) {
    const value = metadata?.[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return null;
}

function profileFromUser(
  user: Awaited<ReturnType<typeof resolveEntitlementContext>>["user"],
): ProfileSummary {
  const metadata = user.user_metadata as Record<string, unknown> | null | undefined;
  return {
    email: user.email ?? "Account owner",
    name: firstMetadataString(metadata, ["name", "full_name", "display_name"]),
    segment: firstMetadataString(metadata, ["segment", "user_segment", "market_segment"]),
    referred_by: firstMetadataString(metadata, [
      "referred_by",
      "referredBy",
      "coach_ref",
      "coachRef",
    ]),
  };
}

async function loadSavedReportPreview(): Promise<{
  reports: SavedReportPreview[];
  error: string | null;
}> {
  try {
    const headerStore = await headers();
    const cookie = headerStore.get("cookie") ?? undefined;
    const url = getAppRouteUrl("/api/agent/reports?limit=5", headerStore);
    const response = await fetch(url, {
      cache: "no-store",
      ...(cookie ? { headers: { cookie } } : {}),
    });

    if (!response.ok) {
      return { reports: [], error: `Reports request failed with HTTP ${response.status}.` };
    }

    const body = (await response.json()) as {
      status?: string;
      message?: string;
      reports?: SavedReportPreview[];
    };

    if (body.status !== "success" || !Array.isArray(body.reports)) {
      return { reports: [], error: body.message ?? "Reports response was invalid." };
    }

    return { reports: body.reports.slice(0, 5), error: null };
  } catch {
    return { reports: [], error: "Reports could not load." };
  }
}

export default async function SettingsPage() {
  const supabase = await createClient();
  let summary: Awaited<ReturnType<typeof loadAccountSummary>> | null = null;
  let profile: ProfileSummary | null = null;
  let savedReports: SavedReportPreview[] = [];
  let savedReportsError: string | null = null;
  let loadError: unknown = null;

  try {
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    summary = await loadAccountSummary({ supabase, user, entitlement });
    profile = profileFromUser(user);
    const reportPreview = await loadSavedReportPreview();
    savedReports = reportPreview.reports;
    savedReportsError = reportPreview.error;
  } catch (error) {
    loadError = error;
  }

  if (summary) {
    return (
      <main className="page" style={{ maxWidth: 1120, margin: "0 auto", width: "100%" }}>
        <header style={{ marginBottom: 26 }}>
          <div className="kicker">Settings</div>
          <h1 className="page-h1" style={{ margin: "4px 0 0" }}>
            Account & billing
          </h1>
          <p className="page-sub">
            Manage your subscription, usage, payment method, and password.
          </p>
        </header>
        <AccountSettingsClient
          summary={summary}
          profile={profile}
          savedReports={savedReports}
          savedReportsError={savedReportsError}
        />
      </main>
    );
  }

  const message =
    loadError instanceof EntitlementError
      ? loadError.message
      : "Account settings are unavailable right now.";
  return (
    <main className="page" style={{ maxWidth: 840, margin: "0 auto", width: "100%" }}>
      <section className="settings-card" role="alert" style={{ padding: 24 }}>
        <div className="kicker">Account unavailable</div>
        <h1 className="page-h1" style={{ margin: "4px 0 8px" }}>
          We could not load billing details.
        </h1>
        <p className="page-sub" style={{ fontStyle: "normal" }}>
          {message}
        </p>
      </section>
    </main>
  );
}
