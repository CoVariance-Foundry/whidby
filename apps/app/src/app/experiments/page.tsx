"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  ChevronDown,
  ChevronRight,
  FlaskConical,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Experiment {
  experiment_id: string;
  hypothesis_id?: string;
  hypothesis_title?: string;
  target_proxy?: string;
  modifications?: Array<{
    param: string;
    current: unknown;
    candidate: unknown;
    description: string;
  }>;
  rollback_condition?: string;
  minimum_detectable_change?: number;
  baseline_score?: number;
  candidate_score?: number;
  delta?: number;
  validated?: boolean;
  learning?: string;
  status?: string;
}

export default function ExperimentsPage() {
  const searchParams = useSearchParams();
  const runId = searchParams.get("run");
  const [sessions, setSessions] = useState<Array<{ run_id: string }>>([]);
  const [selectedRun, setSelectedRun] = useState(runId || "");
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/agent/sessions")
      .then((r) => r.json())
      .then((data) => {
        setSessions(data);
        if (!selectedRun && data.length > 0) {
          setSelectedRun(data[0].run_id);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedRun) return;
    setLoading(true);
    fetch(`/api/agent/experiments/${selectedRun}`)
      .then((r) => r.json())
      .then(setExperiments)
      .catch(() => setExperiments([]))
      .finally(() => setLoading(false));
  }, [selectedRun]);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Experiments</h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Parameter modification results across research runs
          </p>
        </div>
        <select
          value={selectedRun}
          onChange={(e) => setSelectedRun(e.target.value)}
          className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark-alt)] px-3 py-1.5 text-sm text-[var(--color-text-primary)]"
        >
          <option value="">Select a run...</option>
          {sessions.map((s) => (
            <option key={s.run_id} value={s.run_id}>
              {s.run_id}
            </option>
          ))}
        </select>
      </div>

      <div className="rounded-lg border border-[var(--color-dark-border)] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[var(--color-dark-alt)]">
            <tr className="text-left text-[var(--color-text-muted)]">
              <th className="px-4 py-3 font-medium w-8"></th>
              <th className="px-4 py-3 font-medium">Experiment</th>
              <th className="px-4 py-3 font-medium">Target Proxy</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Delta</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-[var(--color-text-muted)]">
                  Loading...
                </td>
              </tr>
            ) : experiments.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-[var(--color-text-muted)]">
                  {selectedRun
                    ? "No experiments found for this run."
                    : "Select a run to view experiments."}
                </td>
              </tr>
            ) : (
              experiments.map((exp) => (
                <ExperimentRow
                  key={exp.experiment_id}
                  experiment={exp}
                  expanded={expandedRow === exp.experiment_id}
                  onToggle={() =>
                    setExpandedRow(
                      expandedRow === exp.experiment_id
                        ? null
                        : exp.experiment_id
                    )
                  }
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ExperimentRow({
  experiment: exp,
  expanded,
  onToggle,
}: {
  experiment: Experiment;
  expanded: boolean;
  onToggle: () => void;
}) {
  const delta = exp.delta ?? 0;

  return (
    <>
      <tr
        className="border-t border-[var(--color-dark-border)] hover:bg-[var(--color-dark-hover)] cursor-pointer"
        onClick={onToggle}
      >
        <td className="px-4 py-3 text-[var(--color-text-muted)]">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <FlaskConical size={14} className="text-[var(--color-node-experiment)]" />
            <div>
              <p className="font-medium text-[var(--color-text-primary)]">
                {exp.hypothesis_title || exp.experiment_id}
              </p>
              <p className="text-xs text-[var(--color-text-muted)] font-mono">
                {exp.experiment_id}
              </p>
            </div>
          </div>
        </td>
        <td className="px-4 py-3 text-[var(--color-text-secondary)]">
          {exp.target_proxy || "—"}
        </td>
        <td className="px-4 py-3">
          <span
            className={cn(
              "inline-block rounded-full px-2 py-0.5 text-xs font-medium",
              exp.status === "planned"
                ? "text-[var(--color-info)] bg-[var(--color-info)]/10"
                : "text-[var(--color-text-muted)] bg-[var(--color-dark)]"
            )}
          >
            {exp.status || "unknown"}
          </span>
        </td>
        <td className="px-4 py-3">
          <DeltaIndicator delta={delta} />
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-[var(--color-dark-border)]">
          <td colSpan={5} className="px-6 py-4 bg-[var(--color-dark)]">
            <div className="grid grid-cols-2 gap-6 text-sm">
              {exp.modifications && exp.modifications.length > 0 && (
                <div>
                  <h4 className="text-xs uppercase tracking-wide text-[var(--color-text-muted)] mb-2">
                    Modifications
                  </h4>
                  <div className="space-y-2">
                    {exp.modifications.map((mod, i) => (
                      <div
                        key={i}
                        className="rounded border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-3"
                      >
                        <p className="font-mono text-xs text-[var(--color-accent)]">
                          {mod.param}
                        </p>
                        <p className="text-xs text-[var(--color-text-secondary)] mt-1">
                          {mod.description}
                        </p>
                        <p className="text-xs text-[var(--color-text-muted)] mt-1">
                          {String(mod.current)} → {String(mod.candidate)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="space-y-3">
                {exp.rollback_condition && (
                  <div>
                    <h4 className="text-xs uppercase tracking-wide text-[var(--color-text-muted)] mb-1">
                      Rollback Condition
                    </h4>
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      {exp.rollback_condition}
                    </p>
                  </div>
                )}
                {exp.minimum_detectable_change != null && (
                  <div>
                    <h4 className="text-xs uppercase tracking-wide text-[var(--color-text-muted)] mb-1">
                      Min Detectable Change
                    </h4>
                    <p className="text-xs text-[var(--color-text-secondary)]">
                      {exp.minimum_detectable_change} points
                    </p>
                  </div>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function DeltaIndicator({ delta }: { delta: number }) {
  if (delta > 0) {
    return (
      <span className="flex items-center gap-1 text-[var(--color-positive)]">
        <ArrowUpRight size={14} />
        +{delta.toFixed(2)}
      </span>
    );
  }
  if (delta < 0) {
    return (
      <span className="flex items-center gap-1 text-[var(--color-negative)]">
        <ArrowDownRight size={14} />
        {delta.toFixed(2)}
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-[var(--color-text-muted)]">
      <Minus size={14} />
      0.00
    </span>
  );
}
