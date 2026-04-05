"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  CheckCircle2,
  XCircle,
  DollarSign,
  Clock,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Session {
  run_id: string;
  completed?: boolean;
  stop_reason?: string;
  iterations_completed?: number;
  total_cost_usd?: number;
  validated_count?: number;
  invalidated_count?: number;
  saved_at?: string;
}

export default function DashboardPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/agent/sessions")
      .then((r) => r.json())
      .then(setSessions)
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  }, []);

  const totalRuns = sessions.length;
  const totalValidated = sessions.reduce(
    (a, s) => a + (s.validated_count || 0),
    0
  );
  const totalCost = sessions.reduce(
    (a, s) => a + (s.total_cost_usd || 0),
    0
  );
  const totalIterations = sessions.reduce(
    (a, s) => a + (s.iterations_completed || 0),
    0
  );

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <p className="text-sm text-[var(--color-text-muted)]">
          Research session history and aggregate metrics
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          icon={<Activity size={18} />}
          label="Total Runs"
          value={String(totalRuns)}
          accent={false}
        />
        <StatCard
          icon={<CheckCircle2 size={18} />}
          label="Validated Hypotheses"
          value={String(totalValidated)}
          accent
        />
        <StatCard
          icon={<DollarSign size={18} />}
          label="Total Cost"
          value={`$${totalCost.toFixed(2)}`}
          accent={false}
        />
        <StatCard
          icon={<Clock size={18} />}
          label="Total Iterations"
          value={String(totalIterations)}
          accent={false}
        />
      </div>

      {/* Run history table */}
      <div className="rounded-lg border border-[var(--color-dark-border)] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[var(--color-dark-alt)]">
            <tr className="text-left text-[var(--color-text-muted)]">
              <th className="px-4 py-3 font-medium">Run ID</th>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Iterations</th>
              <th className="px-4 py-3 font-medium">Stop Reason</th>
              <th className="px-4 py-3 font-medium">Cost</th>
              <th className="px-4 py-3 font-medium">Validated</th>
              <th className="px-4 py-3 font-medium">Invalidated</th>
              <th className="px-4 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-[var(--color-text-muted)]">
                  Loading sessions...
                </td>
              </tr>
            ) : sessions.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-[var(--color-text-muted)]">
                  No research sessions yet. Start one from the Chat page.
                </td>
              </tr>
            ) : (
              sessions.map((s) => (
                <tr
                  key={s.run_id}
                  className="border-t border-[var(--color-dark-border)] hover:bg-[var(--color-dark-hover)]"
                >
                  <td className="px-4 py-3 font-mono text-xs">
                    {s.run_id}
                  </td>
                  <td className="px-4 py-3 text-[var(--color-text-secondary)]">
                    {s.saved_at
                      ? new Date(s.saved_at).toLocaleDateString()
                      : "—"}
                  </td>
                  <td className="px-4 py-3">{s.iterations_completed ?? "—"}</td>
                  <td className="px-4 py-3">
                    <StopReasonBadge reason={s.stop_reason} />
                  </td>
                  <td className="px-4 py-3">
                    ${(s.total_cost_usd ?? 0).toFixed(2)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-[var(--color-positive)]">
                      {s.validated_count ?? 0}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-[var(--color-negative)]">
                      {s.invalidated_count ?? 0}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/experiments?run=${s.run_id}`}
                      className="text-[var(--color-accent)] hover:underline"
                    >
                      <ArrowRight size={14} />
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  accent: boolean;
}) {
  return (
    <div className="rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4">
      <div className="flex items-center gap-2 text-[var(--color-text-muted)] mb-2">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p
        className={cn(
          "text-2xl font-semibold",
          accent
            ? "text-[var(--color-accent)]"
            : "text-[var(--color-text-primary)]"
        )}
      >
        {value}
      </p>
    </div>
  );
}

function StopReasonBadge({ reason }: { reason?: string }) {
  if (!reason) return <span className="text-[var(--color-text-muted)]">—</span>;

  const colors: Record<string, string> = {
    backlog_empty: "text-[var(--color-positive)] bg-[var(--color-positive)]/10",
    max_iterations: "text-[var(--color-warning)] bg-[var(--color-warning)]/10",
    budget_exceeded: "text-[var(--color-negative)] bg-[var(--color-negative)]/10",
    convergence: "text-[var(--color-info)] bg-[var(--color-info)]/10",
  };

  return (
    <span
      className={cn(
        "inline-block rounded-full px-2 py-0.5 text-xs font-medium",
        colors[reason] || "text-[var(--color-text-muted)] bg-[var(--color-dark)]"
      )}
    >
      {reason.replace(/_/g, " ")}
    </span>
  );
}
