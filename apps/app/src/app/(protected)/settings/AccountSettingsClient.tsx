"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Icon, I } from "@/lib/icons";
import { createClient } from "@/lib/supabase/client";
import type { AccountSummary } from "@/lib/account/summary";
import type { PlanKey } from "@/lib/account/entitlements";

const PLAN_ORDER: PlanKey[] = ["free", "plus", "pro"];
const PLAN_COPY: Record<
  PlanKey,
  { name: string; price: string; limit: string; description: string }
> = {
  free: {
    name: "Free",
    price: "$0/mo",
    limit: "Cached reports only",
    description: "Browse shared cached opportunities before you generate fresh reports.",
  },
  plus: {
    name: "Plus",
    price: "$49/mo",
    limit: "10 fresh reports/mo",
    description: "Enough monthly capacity for a focused solo operator.",
  },
  pro: {
    name: "Pro",
    price: "$100/mo",
    limit: "50 fresh reports/mo",
    description: "More room for repeat city and service validation.",
  },
};

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unavailable";
  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

function formatMoney(cents: number): string {
  return `$${Math.round(cents / 100)}`;
}

function usageTone(summary: AccountSummary): "ok" | "warn" | "over" {
  if (summary.monthly_report_limit <= 0) return "ok";
  if (summary.fresh_reports_used >= summary.monthly_report_limit) return "over";
  if (summary.fresh_reports_used / summary.monthly_report_limit >= 0.8) return "warn";
  return "ok";
}

function planStatusCopy(summary: AccountSummary): string {
  if (summary.plan_key === "free") {
    return "Cached market intelligence is available. Fresh reports require Plus or Pro.";
  }
  if (summary.cancel_at_period_end) {
    return `${formatMoney(summary.monthly_price_cents)}/mo. Cancels at period end; access continues through ${formatDate(summary.current_period_end)}.`;
  }
  return `${formatMoney(summary.monthly_price_cents)}/mo. Status: ${summary.subscription_status}.`;
}

export type ProfileSummary = {
  email: string;
  name?: string | null;
  segment?: string | null;
  referred_by?: string | null;
};

export type SavedReportPreview = {
  id: string;
  niche: string;
  city: string;
  archetype_short: string;
  opportunity_score: number | null;
  created_at: string;
};

interface Props {
  summary: AccountSummary;
  profile?: ProfileSummary | null;
  savedReports?: SavedReportPreview[];
  savedReportsError?: string | null;
}

export default function AccountSettingsClient({
  summary,
  profile,
  savedReports = [],
  savedReportsError = null,
}: Props) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(() => {
    const billing = searchParams.get("billing");
    const password = searchParams.get("password");
    if (billing === "success") return "Billing details refreshed.";
    if (billing === "cancelled") return "Billing change cancelled.";
    if (password === "updated") return "Password updated.";
    return null;
  });

  const tone = usageTone(summary);
  const displayEmail = profile?.email ?? summary.email;
  const usagePercent = summary.monthly_report_limit
    ? Math.min(100, Math.round((summary.fresh_reports_used / summary.monthly_report_limit) * 100))
    : 0;

  const cycleLabel = useMemo(() => {
    const start = formatDate(summary.current_period_start);
    const end = formatDate(summary.current_period_end);
    return `${start} to ${end}`;
  }, [summary.current_period_start, summary.current_period_end]);

  async function startCheckout(plan_key: "plus" | "pro") {
    if (!summary.billing_management_available) {
      setNotice("Billing checkout is not available yet.");
      return;
    }
    setBusyAction(`checkout-${plan_key}`);
    try {
      const res = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ plan_key }),
      });
      const body = await res.json();
      if (!res.ok || !body.url) {
        setNotice(body.message ?? "Billing checkout could not start.");
        return;
      }
      window.location.assign(body.url);
    } catch {
      setNotice("Billing checkout could not start.");
    } finally {
      setBusyAction(null);
    }
  }

  async function openPortal(action = "manage") {
    if (!summary.billing_management_available) {
      setNotice("Billing management is not available yet.");
      return;
    }
    if (!summary.stripe_customer_exists) {
      setNotice("Choose Plus or Pro first to create a billing profile.");
      return;
    }
    setBusyAction(`portal-${action}`);
    try {
      const res = await fetch("/api/billing/portal", { method: "POST" });
      const body = await res.json();
      if (!res.ok || !body.url) {
        setNotice(body.message ?? "Billing portal could not open.");
        return;
      }
      window.location.assign(body.url);
    } catch {
      setNotice("Billing portal could not open.");
    } finally {
      setBusyAction(null);
    }
  }

  async function signOut() {
    setBusyAction("sign-out");
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signOut();
      if (error) {
        setNotice(error.message);
        return;
      }
      router.push("/login");
    } catch {
      setNotice("Sign out could not complete.");
    } finally {
      setBusyAction(null);
    }
  }

  async function sendPasswordReset() {
    setBusyAction("password");
    try {
      const supabase = createClient();
      const redirectTo = `${window.location.origin}/auth/callback?next=/settings/password`;
      const { error } = await supabase.auth.resetPasswordForEmail(summary.email, {
        redirectTo,
      });
      if (error) {
        setNotice(error.message);
        return;
      }
      setNotice("Password reset email sent.");
    } catch {
      setNotice("Password reset email could not be sent.");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      {notice && (
        <div
          role="status"
          style={{
            border: "1px solid var(--rule-strong)",
            background: "var(--card)",
            borderRadius: 8,
            padding: "10px 12px",
            color: "var(--ink-2)",
            fontSize: 13,
          }}
        >
          {notice}
        </div>
      )}

      <section className="settings-card" style={{ padding: 22 }}>
        <div className="settings-section-head inline" style={{ padding: 0, marginBottom: 18 }}>
          <div>
            <div className="kicker">Profile</div>
            <h2 className="settings-plan-title" style={{ fontSize: 28 }}>
              Account
            </h2>
          </div>
          <span>Signed in with Supabase Auth.</span>
        </div>
        <div className="settings-meta-grid">
          {profile?.name ? (
            <div>
              <span>Name</span>
              <strong>{profile.name}</strong>
            </div>
          ) : null}
          <div>
            <span>Email</span>
            <strong>{displayEmail}</strong>
          </div>
          {profile?.segment ? (
            <div>
              <span>Segment</span>
              <strong>{profile.segment}</strong>
            </div>
          ) : null}
          {profile?.referred_by ? (
            <div>
              <span>Referred by</span>
              <strong>{profile.referred_by}</strong>
            </div>
          ) : null}
          <div>
            <span>Plan</span>
            <strong>{summary.plan_label}</strong>
          </div>
          <div>
            <span>Account ID</span>
            <strong title={summary.account_id}>{summary.account_id.slice(0, 8)}</strong>
          </div>
        </div>
      </section>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.4fr) minmax(280px, 0.8fr)",
          gap: 18,
          alignItems: "stretch",
        }}
      >
        <div className="settings-card" style={{ padding: 22 }}>
          <div className="kicker">Current plan</div>
          <h2 className="settings-plan-title">{summary.plan_label}</h2>
          <p className="settings-muted">
            {planStatusCopy(summary)}
          </p>
          <div className="settings-meta-grid">
            <div>
              <span>Billing cycle</span>
              <strong>{cycleLabel}</strong>
            </div>
            <div>
              <span>Resets</span>
              <strong>{formatDate(summary.current_period_end)}</strong>
            </div>
            <div>
              <span>Account</span>
              <strong>{summary.email}</strong>
            </div>
          </div>
        </div>

        <div className="settings-card" style={{ padding: 22 }}>
          <div className="settings-row-head">
            <span>Reports this cycle</span>
            <Link href="/reports" className="settings-link">
              View history
            </Link>
          </div>
          <div
            className="settings-usage-count"
            aria-label={`Reports used ${summary.fresh_reports_used} of ${summary.monthly_report_limit}`}
          >
            {summary.fresh_reports_used}
            <span> / {summary.monthly_report_limit}</span>
          </div>
          <div className={`settings-usage-bar ${tone}`}>
            <div style={{ width: `${usagePercent}%` }} />
          </div>
          <p className={`settings-usage-note ${tone}`}>
            {summary.monthly_report_limit === 0
              ? "Free includes cached reports only. Upgrade to generate fresh reports."
              : tone === "over"
                ? `Fresh reports are exhausted until ${formatDate(summary.current_period_end)}.`
                : tone === "warn"
                  ? `${summary.fresh_reports_remaining} fresh reports remain before reset.`
                  : `${summary.fresh_reports_remaining} fresh reports remain.`}
          </p>
        </div>
      </section>

      <section className="settings-card">
        <div className="settings-section-head inline">
          <h3>Saved reports</h3>
          <Link href="/reports" className="settings-link">
            View all
          </Link>
        </div>
        <div style={{ borderTop: "1px solid var(--rule)" }}>
          {savedReportsError ? (
            <div className="settings-row">
              <div>
                <strong>Reports could not load</strong>
                <p>
                  {savedReportsError} The reports archive is still available from the full Reports
                  page.
                </p>
              </div>
              <Link href="/reports" className="btn-ghost">
                Open reports
              </Link>
            </div>
          ) : savedReports.length === 0 ? (
            <div className="settings-row">
              <div>
                <strong>No saved reports yet</strong>
                <p>Run a strategy or explore query to build your first report.</p>
              </div>
              <Link href="/explore" className="btn-ghost">
                Explore markets
              </Link>
            </div>
          ) : (
            savedReports.map((report) => (
              <Link
                key={report.id}
                href={`/reports?open=${encodeURIComponent(report.id)}`}
                className="settings-row"
                style={{ textDecoration: "none" }}
              >
                <div>
                  <strong>
                    {report.niche} · {report.city}
                  </strong>
                  <p>
                    {report.archetype_short} ·{" "}
                    {report.opportunity_score == null
                      ? "No score"
                      : `${report.opportunity_score} opportunity`}{" "}
                    · {formatDate(report.created_at)}
                  </p>
                </div>
                <Icon d={I.arrow} size={14} />
              </Link>
            ))
          )}
        </div>
      </section>

      <section>
        <div className="settings-section-head">
          <h3>Choose your plan</h3>
          <span>Stripe handles checkout, plan changes, and cancellations.</span>
        </div>
        <div className="settings-plan-grid">
          {PLAN_ORDER.map((plan) => (
            <PlanCard
              key={plan}
              plan={plan}
              currentPlan={summary.plan_key}
              current={plan === summary.plan_key}
              disabled={!summary.billing_management_available}
              busy={busyAction === `checkout-${plan}` || busyAction === "portal-manage"}
              onCheckout={startCheckout}
              onPortal={openPortal}
            />
          ))}
        </div>
      </section>

      <section className="settings-card">
        <div className="settings-section-head inline">
          <h3>Payment and invoices</h3>
          <span>Managed securely in Stripe.</span>
        </div>
        <SettingRow
          title="Payment method"
          body={
            summary.stripe_customer_exists
              ? "Payment details are managed in Stripe."
              : "No Stripe billing profile exists yet."
          }
          action={
            <button
              className="btn-ghost"
              type="button"
              disabled={busyAction === "portal-payment" || !summary.billing_management_available}
              onClick={() => openPortal("payment")}
            >
              Manage payment
            </button>
          }
        />
        <SettingRow
          title="Invoice history"
          body="Open Stripe to view receipts and invoice history."
          action={
            <button
              className="btn-ghost"
              type="button"
              disabled={busyAction === "portal-invoices" || !summary.billing_management_available}
              onClick={() => openPortal("invoices")}
            >
              View invoices
            </button>
          }
        />
      </section>

      <section className="settings-card">
        <div className="settings-section-head inline">
          <h3>Password and security</h3>
          <span>Sign-in controls for this account.</span>
        </div>
        <SettingRow
          title="Password"
          body="Send a secure Supabase password reset email to this account."
          action={
            <div
              style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}
            >
              <Link className="btn-ghost" href="/settings/password">
                Manage password
              </Link>
              <button
                className="btn-ghost"
                type="button"
                disabled={busyAction === "password"}
                onClick={sendPasswordReset}
              >
                Send reset email
              </button>
            </div>
          }
        />
        <SettingRow
          title="Two-factor authentication"
          body="Additional sign-in factors are not enabled yet."
          action={<span className="settings-pill">Coming later</span>}
        />
      </section>

      <section className="settings-card">
        <div className="settings-section-head inline">
          <h3>Session</h3>
          <span>Leave this device signed out.</span>
        </div>
        <SettingRow
          title="Sign out"
          body="Ends the current Supabase session and returns to the login screen."
          action={
            <button
              className="btn-ghost"
              type="button"
              disabled={busyAction === "sign-out"}
              onClick={signOut}
            >
              <Icon d={I.x} size={12} />
              {busyAction === "sign-out" ? "Signing out..." : "Sign out"}
            </button>
          }
        />
      </section>

      {summary.plan_key !== "free" && (
        <section className="settings-danger">
          <div>
            <strong>
              {summary.cancel_at_period_end ? "Subscription scheduled to cancel" : "Cancel subscription"}
            </strong>
            <p>
              {summary.cancel_at_period_end
                ? `Access continues through ${formatDate(summary.current_period_end)}. Stripe manages changes to this schedule.`
                : "Stripe will manage cancellation timing. Your reports remain available through the account boundary."}
            </p>
          </div>
          <button
            type="button"
            className="settings-danger-button"
            disabled={busyAction === "portal-cancel" || !summary.billing_management_available}
            onClick={() => openPortal("cancel")}
          >
            {summary.cancel_at_period_end ? "Manage in Stripe" : "Cancel in Stripe"}
          </button>
        </section>
      )}
    </div>
  );
}

function PlanCard({
  plan,
  currentPlan,
  current,
  disabled,
  busy,
  onCheckout,
  onPortal,
}: {
  plan: PlanKey;
  currentPlan: PlanKey;
  current: boolean;
  disabled: boolean;
  busy: boolean;
  onCheckout: (plan: "plus" | "pro") => void;
  onPortal: (action?: string) => void;
}) {
  const copy = PLAN_COPY[plan];
  const shouldCheckout = currentPlan === "free" && plan !== "free";
  const actionLabel =
    plan === "free" ? "Manage downgrade" : shouldCheckout ? `Upgrade to ${copy.name}` : "Change in Stripe";
  return (
    <article className={`settings-plan-card ${current ? "current" : ""}`}>
      <div>
        <div className="settings-row-head">
          <h4>{copy.name}</h4>
          {current && <span className="settings-pill">Current</span>}
        </div>
        <div className="settings-plan-price">{copy.price}</div>
        <p>{copy.limit}</p>
        <span>{copy.description}</span>
      </div>
      {current ? (
        <button className="btn-ghost" type="button" disabled>
          Current plan
        </button>
      ) : shouldCheckout ? (
        <button
          className="btn-primary"
          type="button"
          disabled={disabled || busy}
          onClick={() => onCheckout(plan)}
        >
          <Icon d={I.arrowUp} /> {actionLabel}
        </button>
      ) : (
        <button
          className={plan === "free" ? "btn-ghost" : "btn-primary"}
          type="button"
          disabled={disabled || busy}
          onClick={() => onPortal("manage")}
        >
          {plan === "free" ? null : <Icon d={I.arrowUp} />}
          {actionLabel}
        </button>
      )}
    </article>
  );
}

function SettingRow({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action: ReactNode;
}) {
  return (
    <div className="settings-row">
      <div>
        <strong>{title}</strong>
        <p>{body}</p>
      </div>
      {action}
    </div>
  );
}
