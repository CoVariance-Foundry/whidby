"use client";

import { useEffect, useState } from "react";
import {
  Lightbulb,
  ArrowUpRight,
  Shield,
  ShieldAlert,
  ShieldCheck,
  FileText,
  CheckCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Recommendation {
  id: string;
  hypothesis_id: string;
  title: string;
  description: string;
  impact_score: number;
  confidence: string;
  priority_score: number;
  cost_usd: number;
  status: string;
  evidence: {
    baseline_score: number;
    candidate_score: number;
    delta: number;
    experiment_id: string;
  };
}

interface SessionSummary {
  run_id: string;
  recommendations?: Recommendation[];
}

export default function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterConfidence, setFilterConfidence] = useState<string>("all");
  const [reviewed, setReviewed] = useState<Set<string>>(new Set());

  useEffect(() => {
    async function loadRecommendations() {
      try {
        const sessionsRes = await fetch("/api/agent/sessions");
        const sessions: Array<{ run_id: string }> = await sessionsRes.json();

        const allRecs: Recommendation[] = [];
        for (const session of sessions.slice(0, 10)) {
          try {
            const detailRes = await fetch(
              `/api/agent/sessions/${session.run_id}`
            );
            const detail = await detailRes.json();
            const progress = detail.progress || [];
            for (const entry of progress) {
              if (entry.validated && entry.experiment_id) {
                allRecs.push({
                  id: entry.experiment_id,
                  hypothesis_id: entry.hypothesis_id || "",
                  title: `Improvement from experiment ${entry.experiment_id}`,
                  description: entry.learning || "",
                  impact_score: Math.abs(entry.delta || 0),
                  confidence:
                    Math.abs(entry.delta || 0) > 5
                      ? "high"
                      : Math.abs(entry.delta || 0) > 2
                        ? "medium"
                        : "low",
                  priority_score: Math.abs(entry.delta || 0),
                  cost_usd: entry.cost_usd || 0,
                  status: "proposed",
                  evidence: {
                    baseline_score: entry.baseline_score || 0,
                    candidate_score: entry.candidate_score || 0,
                    delta: entry.delta || 0,
                    experiment_id: entry.experiment_id || "",
                  },
                });
              }
            }
          } catch {
            /* skip failed session detail */
          }
        }
        allRecs.sort((a, b) => b.priority_score - a.priority_score);
        setRecommendations(allRecs);
      } catch {
        setRecommendations([]);
      } finally {
        setLoading(false);
      }
    }
    loadRecommendations();
  }, []);

  const filtered =
    filterConfidence === "all"
      ? recommendations
      : recommendations.filter((r) => r.confidence === filterConfidence);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Recommendations</h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Prioritized improvements from validated experiments
          </p>
        </div>
        <div className="flex gap-2">
          {["all", "high", "medium", "low"].map((level) => (
            <button
              key={level}
              onClick={() => setFilterConfidence(level)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs transition-colors",
                filterConfidence === level
                  ? "bg-[var(--color-accent)] text-white"
                  : "border border-[var(--color-dark-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-dark-hover)]"
              )}
            >
              {level === "all" ? "All" : level.charAt(0).toUpperCase() + level.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-[var(--color-text-muted)]">
          Loading recommendations...
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-[var(--color-text-muted)] gap-2">
          <Lightbulb size={48} strokeWidth={1} />
          <p className="text-sm">No recommendations yet.</p>
          <p className="text-xs">
            Run a research session to generate improvement proposals.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((rec) => (
            <RecommendationCard
              key={rec.id}
              rec={rec}
              isReviewed={reviewed.has(rec.id)}
              onReview={() =>
                setReviewed((prev) => new Set([...prev, rec.id]))
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}

function RecommendationCard({
  rec,
  isReviewed,
  onReview,
}: {
  rec: Recommendation;
  isReviewed: boolean;
  onReview: () => void;
}) {
  const ConfidenceIcon =
    rec.confidence === "high"
      ? ShieldCheck
      : rec.confidence === "medium"
        ? Shield
        : ShieldAlert;

  const confidenceColors: Record<string, string> = {
    high: "text-[var(--color-positive)]",
    medium: "text-[var(--color-warning)]",
    low: "text-[var(--color-text-muted)]",
  };

  return (
    <div
      className={cn(
        "rounded-lg border bg-[var(--color-dark-card)] p-5 transition-colors",
        isReviewed
          ? "border-[var(--color-accent)]/30"
          : "border-[var(--color-dark-border)]"
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <Lightbulb
            size={20}
            className="text-[var(--color-node-recommendation)]"
          />
          <div>
            <h3 className="text-sm font-medium text-[var(--color-text-primary)]">
              {rec.title}
            </h3>
            <p className="text-xs text-[var(--color-text-muted)] font-mono">
              {rec.hypothesis_id}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className={cn("flex items-center gap-1", confidenceColors[rec.confidence])}>
            <ConfidenceIcon size={14} />
            <span className="text-xs font-medium">{rec.confidence}</span>
          </div>
          <button
            onClick={onReview}
            disabled={isReviewed}
            className={cn(
              "flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              isReviewed
                ? "bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                : "border border-[var(--color-dark-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-dark-hover)]"
            )}
          >
            {isReviewed ? (
              <>
                <CheckCircle size={12} />
                Reviewed
              </>
            ) : (
              "Mark Reviewed"
            )}
          </button>
        </div>
      </div>

      {rec.description && (
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed mb-4 whitespace-pre-wrap">
          {rec.description}
        </p>
      )}

      <div className="flex items-center gap-6 text-xs">
        <div>
          <span className="text-[var(--color-text-muted)]">Impact: </span>
          <span className="font-medium text-[var(--color-text-primary)]">
            {rec.impact_score.toFixed(3)}
          </span>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)]">Priority: </span>
          <span className="font-medium text-[var(--color-text-primary)]">
            {rec.priority_score.toFixed(3)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[var(--color-text-muted)]">Delta: </span>
          <span
            className={cn(
              "font-medium flex items-center gap-0.5",
              rec.evidence.delta > 0
                ? "text-[var(--color-positive)]"
                : "text-[var(--color-negative)]"
            )}
          >
            <ArrowUpRight size={12} />
            {rec.evidence.delta > 0 ? "+" : ""}
            {rec.evidence.delta.toFixed(3)}
          </span>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)]">Baseline: </span>
          <span>{rec.evidence.baseline_score.toFixed(2)}</span>
          <span className="text-[var(--color-text-muted)]"> → </span>
          <span>{rec.evidence.candidate_score.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)]">Cost: </span>
          <span>${rec.cost_usd.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
}
