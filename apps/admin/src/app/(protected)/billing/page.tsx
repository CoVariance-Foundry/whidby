"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

type BillingIssue = {
  id: string;
  severity: "critical" | "error" | "warning" | "info";
  status: "open" | "resolved";
  event_type: string;
  source: string;
  account_id: string | null;
  user_id: string | null;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  stripe_checkout_session_id: string | null;
  stripe_event_id: string | null;
  public_message: string;
  internal_message: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  resolved_at: string | null;
};

type StatusFilter = "open" | "resolved" | "all";
type SeverityFilter = "all" | "critical" | "error" | "warning";

const statusOptions: StatusFilter[] = ["open", "resolved", "all"];
const severityOptions: SeverityFilter[] = ["all", "critical", "error", "warning"];

export default function BillingIssuesPage() {
  const [issues, setIssues] = useState<BillingIssue[]>([]);
  const [status, setStatus] = useState<StatusFilter>("open");
  const [severity, setSeverity] = useState<SeverityFilter>("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadIssues = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ status });
    if (severity !== "all") params.set("severity", severity);

    try {
      const response = await fetch(`/api/billing/issues?${params.toString()}`);
      const body = await response.json();
      if (!response.ok || body.status !== "success") {
        setError(body.message ?? "Billing issues could not load.");
        setIssues([]);
        return;
      }
      setIssues(Array.isArray(body.issues) ? body.issues : []);
    } catch {
      setError("Billing issues could not load.");
      setIssues([]);
    } finally {
      setLoading(false);
    }
  }, [severity, status]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadIssues();
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [loadIssues]);

  const counts = useMemo(
    () => ({
      open: issues.filter((issue) => issue.status === "open").length,
      critical: issues.filter((issue) => issue.severity === "critical").length,
      warnings: issues.filter((issue) => issue.severity === "warning").length,
    }),
    [issues],
  );

  async function resolveIssue(issueId: string) {
    const response = await fetch(`/api/billing/issues/${issueId}/resolve`, {
      method: "POST",
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setError(body.message ?? "Billing issue could not be resolved.");
      return;
    }
    await loadIssues();
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Billing issues</h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Stripe checkout, portal, and webhook issues requiring admin attention
          </p>
        </div>
        <button
          type="button"
          onClick={() => loadIssues()}
          className="inline-flex items-center gap-2 rounded-md border border-[var(--color-dark-border)] px-3 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-dark-hover)]"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Open" value={String(counts.open)} tone="info" />
        <StatCard label="Critical" value={String(counts.critical)} tone="critical" />
        <StatCard label="Warnings" value={String(counts.warnings)} tone="warning" />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <FilterSelect label="Status" value={status} values={statusOptions} onChange={setStatus} />
        <FilterSelect
          label="Severity"
          value={severity}
          values={severityOptions}
          onChange={setSeverity}
        />
      </div>

      {error && (
        <div role="alert" className="rounded-md border border-[var(--color-negative)]/40 bg-[var(--color-negative)]/10 p-3 text-sm text-[var(--color-negative)]">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-[var(--color-dark-border)]">
        <table className="w-full text-sm">
          <thead className="bg-[var(--color-dark-alt)]">
            <tr className="text-left text-[var(--color-text-muted)]">
              <th className="w-8 px-4 py-3 font-medium"></th>
              <th className="px-4 py-3 font-medium">Issue</th>
              <th className="px-4 py-3 font-medium">Severity</th>
              <th className="px-4 py-3 font-medium">Source</th>
              <th className="px-4 py-3 font-medium">Created</th>
              <th className="px-4 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-[var(--color-text-muted)]">
                  Loading billing issues...
                </td>
              </tr>
            ) : issues.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-[var(--color-text-muted)]">
                  No billing issues match this view.
                </td>
              </tr>
            ) : (
              issues.map((issue) => (
                <IssueRow
                  key={issue.id}
                  issue={issue}
                  expanded={expanded === issue.id}
                  onToggle={() => setExpanded(expanded === issue.id ? null : issue.id)}
                  onResolve={() => resolveIssue(issue.id)}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({ label, value, tone }: { label: string; value: string; tone: "info" | "critical" | "warning" }) {
  const color =
    tone === "critical"
      ? "text-[var(--color-negative)]"
      : tone === "warning"
        ? "text-[var(--color-warning)]"
        : "text-[var(--color-info)]";
  return (
    <div className="rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4">
      <div className="mb-2 flex items-center gap-2 text-[var(--color-text-muted)]">
        {tone === "critical" ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
        <span className="text-xs">{label}</span>
      </div>
      <p className={cn("text-2xl font-semibold", color)}>{value}</p>
    </div>
  );
}

function FilterSelect<T extends string>({
  label,
  value,
  values,
  onChange,
}: {
  label: string;
  value: T;
  values: T[];
  onChange: (value: T) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
        className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark-alt)] px-3 py-1.5 text-sm text-[var(--color-text-primary)]"
      >
        {values.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function IssueRow({
  issue,
  expanded,
  onToggle,
  onResolve,
}: {
  issue: BillingIssue;
  expanded: boolean;
  onToggle: () => void;
  onResolve: () => void;
}) {
  return (
    <>
      <tr className="border-t border-[var(--color-dark-border)] hover:bg-[var(--color-dark-hover)]">
        <td className="px-4 py-3 text-[var(--color-text-muted)]">
          <button type="button" aria-label={`Toggle ${issue.event_type}`} onClick={onToggle}>
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        </td>
        <td className="px-4 py-3">
          <p className="font-medium text-[var(--color-text-primary)]">{issue.public_message}</p>
          <p className="font-mono text-xs text-[var(--color-text-muted)]">{issue.event_type}</p>
        </td>
        <td className="px-4 py-3">
          <SeverityBadge severity={issue.severity} />
        </td>
        <td className="px-4 py-3 text-[var(--color-text-secondary)]">{issue.source}</td>
        <td className="px-4 py-3 text-[var(--color-text-secondary)]">
          {new Date(issue.created_at).toLocaleString()}
        </td>
        <td className="px-4 py-3 text-right">
          {issue.status === "open" ? (
            <button
              type="button"
              onClick={onResolve}
              className="rounded-md border border-[var(--color-dark-border)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-dark-hover)]"
            >
              Mark resolved
            </button>
          ) : (
            <span className="text-xs text-[var(--color-positive)]">Resolved</span>
          )}
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-[var(--color-dark-border)]">
          <td colSpan={6} className="bg-[var(--color-dark)] px-6 py-4">
            <dl className="grid grid-cols-2 gap-4 text-xs">
              <Detail label="Account" value={issue.account_id} />
              <Detail label="User" value={issue.user_id} />
              <Detail label="Stripe customer" value={issue.stripe_customer_id} />
              <Detail label="Stripe subscription" value={issue.stripe_subscription_id} />
              <Detail label="Stripe checkout" value={issue.stripe_checkout_session_id} />
              <Detail label="Stripe event" value={issue.stripe_event_id} />
              <Detail label="Internal message" value={issue.internal_message} wide />
              <Detail label="Metadata" value={JSON.stringify(issue.metadata ?? {}, null, 2)} wide />
            </dl>
          </td>
        </tr>
      )}
    </>
  );
}

function SeverityBadge({ severity }: { severity: BillingIssue["severity"] }) {
  const className =
    severity === "critical"
      ? "text-[var(--color-negative)] bg-[var(--color-negative)]/10"
      : severity === "error"
        ? "text-[var(--color-negative)] bg-[var(--color-negative)]/10"
        : severity === "warning"
          ? "text-[var(--color-warning)] bg-[var(--color-warning)]/10"
          : "text-[var(--color-info)] bg-[var(--color-info)]/10";
  return (
    <span className={cn("inline-block rounded-full px-2 py-0.5 text-xs font-medium", className)}>
      {severity}
    </span>
  );
}

function Detail({ label, value, wide = false }: { label: string; value?: string | null; wide?: boolean }) {
  return (
    <div className={wide ? "col-span-2" : ""}>
      <dt className="mb-1 text-[var(--color-text-muted)]">{label}</dt>
      <dd className="whitespace-pre-wrap break-all font-mono text-[var(--color-text-secondary)]">
        {value || "—"}
      </dd>
    </div>
  );
}
