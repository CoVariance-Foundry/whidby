import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { EntitlementError, resolveEntitlementContext } from "@/lib/account/entitlements";
import { loadAccountSummary } from "@/lib/account/summary";
import { createClient } from "@/lib/supabase/server";
import AccountSettingsClient from "./AccountSettingsClient";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const supabase = await createClient();
  let summary: Awaited<ReturnType<typeof loadAccountSummary>> | null = null;
  let loadError: unknown = null;

  try {
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    summary = await loadAccountSummary({ supabase, user, entitlement });
  } catch (error) {
    loadError = error;
  }

  if (summary) {
    return (
      <div className="app">
        <Sidebar active="settings" planLabel={summary.plan_label} />
        <div className="main">
          <Topbar crumbs={["Settings", "Account & billing"]} />
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
            <AccountSettingsClient summary={summary} />
          </main>
        </div>
      </div>
    );
  }

  const message =
    loadError instanceof EntitlementError
      ? loadError.message
      : "Account settings are unavailable right now.";
  return (
    <div className="app">
      <Sidebar active="settings" />
      <div className="main">
        <Topbar crumbs={["Settings", "Account & billing"]} />
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
      </div>
    </div>
  );
}
