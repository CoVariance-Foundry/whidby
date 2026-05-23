"use client";

import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Icon, I } from "@/lib/icons";
import { ARCHETYPES } from "@/lib/archetypes";
import { scoreToneForValue } from "@/lib/design-tokens";
import type { FullReportData, ReportMetro } from "@/lib/niche-finder/types";
import { ScoreBar, ScoreCircle } from "@/components/ScoreVisuals";
import ScoreInfoHover from "@/components/reports/ScoreInfoHover";
import ScoreBreakdownTabs from "@/components/reports/ScoreBreakdownTabs";
import ReportActions from "@/components/reports/ReportActions";
import type { ScoreKey } from "@/lib/reports/score-explainers";

interface Props {
  report: FullReportData;
  onClose: () => void;
  onDelete?: (reportId: string) => Promise<void>;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function archetypeLabel(id?: string): { label: string; glyph: string } {
  if (!id) return { label: "Unknown", glyph: "arch-mixed" };
  const normalized = id.toUpperCase().replace(/[\s-]+/g, "_");
  const found = ARCHETYPES.find(
    (a) =>
      a.id === id ||
      a.id === normalized ||
      a.title.toUpperCase().replace(/[\s-]+/g, "_") === normalized,
  );
  return found
    ? { label: found.short, glyph: found.glyph }
    : { label: humanizeEnum(id), glyph: "arch-mixed" };
}

function humanizeEnum(raw: string): string {
  return raw
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/^\w/, (c) => c.toUpperCase());
}

const DIFFICULTY_LABELS: Record<string, string> = {
  EASY: "Easy",
  MODERATE: "Moderate",
  HARD: "Hard",
  VERY_HARD: "Very hard",
};

const EXPOSURE_LABELS: Record<string, string> = {
  AI_SHIELDED: "Shielded",
  AI_MINIMAL: "Minimal",
  AI_MODERATE: "Moderate",
  AI_EXPOSED: "Exposed",
};

function Pill({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: 999,
        fontSize: 11,
        fontFamily: "var(--sans)",
        fontWeight: 600,
        letterSpacing: "0.02em",
        textTransform: "uppercase" as const,
        background: "var(--paper-alt)",
        color: "var(--ink-2)",
        border: "1px solid var(--rule)",
        ...style,
      }}
    >
      {children}
    </span>
  );
}

function ScoreCell({ label, value, scoreKey }: { label: string; value: number | undefined; scoreKey?: ScoreKey }) {
  const v = value ?? 0;
  const tone = scoreToneForValue(value);

  return (
    <div style={{ minWidth: 0 }}>
      <div
        style={{
          fontFamily: "var(--serif)",
          fontStyle: "italic",
          fontSize: 11,
          color: "var(--ink-3)",
          marginBottom: 4,
          display: "flex",
          alignItems: "center",
        }}
      >
        {label}
        {scoreKey && <ScoreInfoHover scoreKey={scoreKey} />}
      </div>
      <div
        style={{
          fontFamily: "var(--mono)",
          fontVariantNumeric: "tabular-nums",
          fontWeight: 800,
          fontSize: 22,
          color: tone.text,
          lineHeight: 1,
        }}
      >
        {value != null ? Math.round(v) : "—"}
      </div>
      <div style={{ marginTop: 6 }}>
        <ScoreBar value={value} label={label} hideLabel hideValue />
      </div>
    </div>
  );
}

function MetroCard({ metro }: { metro: ReportMetro }) {
  const arch = archetypeLabel(metro.serp_archetype);
  const pop = metro.population
    ? metro.population.toLocaleString("en-US")
    : null;

  return (
    <div
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: "20px 22px",
      }}
    >
      {/* Metro header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 16,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontFamily: "var(--serif)",
            fontSize: 17,
            fontWeight: 600,
            color: "var(--ink)",
          }}
        >
          {metro.cbsa_name}
        </span>
        {pop && (
          <Pill>
            Pop. {pop}
          </Pill>
        )}
        <span
          className={arch.glyph}
          style={{
            display: "inline-block",
            padding: "2px 10px",
            borderRadius: 999,
            fontSize: 11,
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.02em",
          }}
        >
          {arch.label}
        </span>
      </div>

      {/* Scores grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "16px 20px",
          marginBottom: 16,
        }}
      >
        <ScoreCell label="Demand" value={metro.scores.demand} scoreKey="demand" />
        <ScoreCell label="Organic comp." value={metro.scores.organic_competition} scoreKey="organic_competition" />
        <ScoreCell label="Local comp." value={metro.scores.local_competition} scoreKey="local_competition" />
        <ScoreCell label="Monetization" value={metro.scores.monetization} scoreKey="monetization" />
        <ScoreCell label="AI resilience" value={metro.scores.ai_resilience} scoreKey="ai_resilience" />
        <ScoreCell label="Opportunity" value={metro.scores.opportunity} scoreKey="opportunity" />
      </div>

      {/* Badges row */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        {metro.difficulty_tier && (
          <Pill>Difficulty: {DIFFICULTY_LABELS[metro.difficulty_tier] ?? humanizeEnum(metro.difficulty_tier)}</Pill>
        )}
        {metro.ai_exposure && (
          <Pill>AI exposure: {EXPOSURE_LABELS[metro.ai_exposure] ?? humanizeEnum(metro.ai_exposure)}</Pill>
        )}
        {metro.scores.confidence && (
          <Pill>Confidence: {metro.scores.confidence.score ?? "—"}</Pill>
        )}
      </div>

      {/* Score breakdown tabs */}
      {metro.signals && Object.keys(metro.signals).length > 0 && (
        <ScoreBreakdownTabs signals={metro.signals} scores={metro.scores} />
      )}

      {/* Guidance */}
      {metro.guidance && (metro.guidance.summary || metro.guidance.action_items) && (
        <div
          style={{
            borderTop: "1px solid var(--rule)",
            paddingTop: 14,
          }}
        >
          <div
            style={{
              fontFamily: "var(--serif)",
              fontStyle: "italic",
              fontSize: 11,
              color: "var(--ink-3)",
              marginBottom: 6,
            }}
          >
            Guidance
          </div>
          {metro.guidance.summary && (
            <p
              style={{
                fontFamily: "var(--sans)",
                fontSize: 13,
                color: "var(--ink-2)",
                margin: "0 0 8px",
                lineHeight: 1.5,
              }}
            >
              {metro.guidance.summary}
            </p>
          )}
          {metro.guidance.action_items && metro.guidance.action_items.length > 0 && (
            <ul
              style={{
                margin: 0,
                paddingLeft: 18,
                fontFamily: "var(--sans)",
                fontSize: 12.5,
                color: "var(--ink-2)",
                lineHeight: 1.6,
              }}
            >
              {metro.guidance.action_items.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default function ReportDetailModal({ report, onClose, onDelete }: Props) {
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeBtnRef.current?.focus();
  }, []);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const meta = report.meta;

  return createPortal(
    <div
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label={`Report: ${report.niche_keyword}`}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(31, 27, 22, 0.35)",
        zIndex: 100,
        display: "grid",
        placeItems: "center",
        padding: 24,
      }}
    >
      <div
        style={{
          background: "var(--card)",
          border: "1px solid var(--rule-strong)",
          borderRadius: 14,
          boxShadow: "0 20px 60px rgba(31, 27, 22, 0.22)",
          width: "100%",
          maxWidth: 860,
          maxHeight: "calc(100vh - 48px)",
          overflowY: "auto",
          position: "relative",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "22px 24px 18px",
            borderBottom: "1px solid var(--rule)",
            position: "sticky",
            top: 0,
            background: "var(--card)",
            zIndex: 1,
            borderRadius: "14px 14px 0 0",
          }}
        >
          <button
            ref={closeBtnRef}
            onClick={onClose}
            aria-label="Close"
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              width: 32,
              height: 32,
              borderRadius: 8,
              display: "grid",
              placeItems: "center",
              color: "var(--ink-2)",
              border: "1px solid var(--rule-strong)",
              background: "var(--card)",
              cursor: "pointer",
            }}
          >
            <Icon d={I.x} size={14} />
          </button>

          <div
            style={{
              fontFamily: "var(--serif)",
              fontStyle: "italic",
              fontSize: 12,
              color: "var(--accent-ink)",
              letterSpacing: "0.02em",
              marginBottom: 6,
            }}
          >
            Report
          </div>
          <h2
            style={{
              fontFamily: "var(--serif)",
              fontSize: 24,
              fontWeight: 600,
              letterSpacing: 0,
              color: "var(--ink)",
              margin: 0,
              paddingRight: 40,
            }}
          >
            {report.niche_keyword}
          </h2>
          <div
            style={{
              fontFamily: "var(--serif)",
              fontStyle: "italic",
              fontSize: 14,
              color: "var(--ink-2)",
              marginTop: 4,
            }}
          >
            {report.geo_target} &middot; {formatDate(report.created_at)}
          </div>
          <div style={{ display: "flex", gap: 6, marginTop: 10, flexWrap: "wrap", alignItems: "center" }}>
            <Pill>v{report.spec_version}</Pill>
            <Pill>{report.strategy_profile}</Pill>
            <Pill>{report.report_depth}</Pill>

            <div style={{ marginLeft: "auto" }}>
              <ReportActions report={report} onDelete={onDelete} />
            </div>
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: "20px 24px 28px" }}>
          {/* Opportunity headline */}
          {report.metros.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <div
                style={{
                  fontFamily: "var(--serif)",
                  fontStyle: "italic",
                  fontSize: 11,
                  color: "var(--ink-3)",
                  marginBottom: 4,
                  display: "flex",
                  alignItems: "center",
                }}
              >
                Top opportunity score
                <ScoreInfoHover scoreKey="opportunity" />
              </div>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 14 }}>
                <ScoreCircle
                  value={report.metros[0].scores.opportunity}
                  label="Top opportunity score"
                  size={78}
                />
                <div style={{ width: 132, paddingBottom: 10 }}>
                  <ScoreBar
                    value={report.metros[0].scores.opportunity}
                    label="Top opportunity score"
                    hideLabel
                    hideValue
                  />
                </div>
              </div>
            </div>
          )}

          {/* Metros */}
          {report.metros.length > 0 && (
            <section style={{ marginBottom: 28 }}>
              <h3
                style={{
                  fontFamily: "var(--serif)",
                  fontSize: 16,
                  fontWeight: 600,
                  color: "var(--ink)",
                  margin: "0 0 12px",
                }}
              >
                Metro{report.metros.length > 1 ? "s" : ""} ({report.metros.length})
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {report.metros.map((m) => (
                  <MetroCard key={m.cbsa_code} metro={m} />
                ))}
              </div>
            </section>
          )}

          {/* Meta */}
          {meta && Object.keys(meta).length > 0 && (
            <details
              style={{
                border: "1px solid var(--rule)",
                borderRadius: 10,
                background: "var(--card)",
              }}
            >
              <summary
                style={{
                  padding: "10px 14px",
                  fontFamily: "var(--serif)",
                  fontStyle: "italic",
                  fontSize: 12,
                  color: "var(--ink-3)",
                  cursor: "pointer",
                  listStyle: "none",
                }}
              >
                Meta &amp; cost details
              </summary>
              <div
                style={{
                  padding: "0 14px 14px",
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: "10px 16px",
                }}
              >
                {meta.processing_time_seconds != null && (
                  <div>
                    <div style={{ fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 11, color: "var(--ink-3)" }}>
                      Processing time
                    </div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 13, color: "var(--ink)" }}>
                      {Number(meta.processing_time_seconds).toFixed(1)}s
                    </div>
                  </div>
                )}
                {meta.total_api_calls != null && (
                  <div>
                    <div style={{ fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 11, color: "var(--ink-3)" }}>
                      API calls
                    </div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 13, color: "var(--ink)" }}>
                      {String(meta.total_api_calls)}
                    </div>
                  </div>
                )}
                {meta.total_cost_usd != null && (
                  <div>
                    <div style={{ fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 11, color: "var(--ink-3)" }}>
                      Cost
                    </div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 13, color: "var(--ink)" }}>
                      ${Number(meta.total_cost_usd).toFixed(4)}
                    </div>
                  </div>
                )}
              </div>
            </details>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
