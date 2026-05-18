"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useSearchParams } from "next/navigation";
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

interface Props {
  summary: AccountSummary;
}

export default function AccountSettingsClient({ summary }: Props) {
  const searchParams = useSearchParams();
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
            <button
              className="btn-ghost"
              type="button"
              disabled={busyAction === "password"}
              onClick={sendPasswordReset}
            >
              Send reset email
            </button>
          }
        />
        <SettingRow
          title="Two-factor authentication"
          body="Additional sign-in factors are not enabled yet."
          action={<span className="settings-pill">Coming later</span>}
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
