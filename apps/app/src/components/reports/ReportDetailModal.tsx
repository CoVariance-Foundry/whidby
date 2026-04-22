"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Icon, I } from "@/lib/icons";
import { ARCHETYPES } from "@/lib/archetypes";
import type { FullReportData, ReportMetro } from "@/lib/niche-finder/types";
import ScoreInfoHover from "@/components/reports/ScoreInfoHover";
import ScoreBreakdownTabs from "@/components/reports/ScoreBreakdownTabs";
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

function scoreColor(score: number): string {
  if (score >= 75) return "#0f7a57";
  if (score >= 50) return "#a05a00";
  return "#a3292d";
}

function scoreBarBg(score: number): string {
  if (score >= 75) return "#dfede6";
  if (score >= 50) return "#f6ebd4";
  return "#f3e1e1";
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
          fontFamily: "var(--serif)",
          fontVariantNumeric: "tabular-nums",
          fontWeight: 600,
          fontSize: 22,
          letterSpacing: "-0.4px",
          color: scoreColor(v),
          lineHeight: 1,
        }}
      >
        {value != null ? Math.round(v) : "—"}
      </div>
      <div
        style={{
          marginTop: 6,
          height: 3,
          background: scoreBarBg(v),
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${Math.min(v, 100)}%`,
            background: scoreColor(v),
            borderRadius: 2,
          }}
        />
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

function KeywordTable({
  keywords,
}: {
  keywords: { keyword: string; tier?: number; intent?: string; search_volume?: number; cpc?: number }[];
}) {
  return (
    <div
      style={{
        border: "1px solid var(--rule)",
        borderRadius: 10,
        overflow: "hidden",
        background: "var(--card)",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0,2.5fr) 60px 100px 90px 70px",
          padding: "8px 14px",
          background: "var(--paper-alt)",
          borderBottom: "1px solid var(--rule)",
          fontFamily: "var(--serif)",
          fontStyle: "italic",
          fontSize: 11,
          color: "var(--ink-3)",
          gap: 10,
        }}
      >
        <span>Keyword</span>
        <span>Tier</span>
        <span>Intent</span>
        <span style={{ textAlign: "right" }}>Volume</span>
        <span style={{ textAlign: "right" }}>CPC</span>
      </div>
      {keywords.map((kw, i) => (
        <div
          key={i}
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,2.5fr) 60px 100px 90px 70px",
            padding: "8px 14px",
            borderBottom: "1px solid var(--rule)",
            fontFamily: "var(--sans)",
            fontSize: 12.5,
            color: "var(--ink)",
            gap: 10,
            alignItems: "center",
          }}
        >
          <span
            style={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={kw.keyword}
          >
            {kw.keyword}
          </span>
          <span>
            {kw.tier != null && (
              <Pill style={{ fontSize: 10, padding: "1px 7px" }}>T{kw.tier}</Pill>
            )}
          </span>
          <span style={{ fontSize: 11.5, color: "var(--ink-2)" }}>
            {kw.intent ?? "—"}
          </span>
          <span
            style={{
              textAlign: "right",
              fontFamily: "var(--mono)",
              fontSize: 12,
            }}
          >
            {kw.search_volume != null ? kw.search_volume.toLocaleString() : "—"}
          </span>
          <span
            style={{
              textAlign: "right",
              fontFamily: "var(--mono)",
              fontSize: 12,
            }}
          >
            {kw.cpc != null ? `$${kw.cpc.toFixed(2)}` : "—"}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function ReportDetailModal({ report, onClose, onDelete }: Props) {
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

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

  const keywords = report.keyword_expansion?.expanded_keywords;
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
              letterSpacing: "-0.3px",
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

            {onDelete && (
              <div style={{ marginLeft: "auto" }}>
                {!confirmDelete ? (
                  <button
                    type="button"
                    onClick={() => setConfirmDelete(true)}
                    disabled={deleting}
                    style={{
                      fontFamily: "var(--sans)",
                      fontSize: 12,
                      fontWeight: 500,
                      color: "var(--ink-3)",
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      padding: "4px 8px",
                      borderRadius: 6,
                      transition: "color 0.15s",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "var(--danger)")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "var(--ink-3)")}
                  >
                    Delete report
                  </button>
                ) : (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      background: "var(--danger-soft)",
                      border: "1px solid var(--danger)",
                      borderRadius: 8,
                      padding: "6px 12px",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "var(--serif)",
                        fontStyle: "italic",
                        fontSize: 12,
                        color: "var(--danger)",
                      }}
                    >
                      This can&apos;t be undone
                    </span>
                    <button
                      type="button"
                      disabled={deleting}
                      onClick={async () => {
                        setDeleting(true);
                        await onDelete(report.id);
                      }}
                      style={{
                        fontFamily: "var(--sans)",
                        fontSize: 12,
                        fontWeight: 600,
                        color: "#fff",
                        background: "var(--danger)",
                        border: "none",
                        borderRadius: 6,
                        padding: "4px 12px",
                        cursor: deleting ? "wait" : "pointer",
                        opacity: deleting ? 0.6 : 1,
                      }}
                    >
                      {deleting ? "Deleting…" : "Delete"}
                    </button>
                    <button
                      type="button"
                      disabled={deleting}
                      onClick={() => setConfirmDelete(false)}
                      style={{
                        fontFamily: "var(--sans)",
                        fontSize: 12,
                        fontWeight: 500,
                        color: "var(--ink-2)",
                        background: "none",
                        border: "1px solid var(--rule)",
                        borderRadius: 6,
                        padding: "4px 10px",
                        cursor: "pointer",
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            )}
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
                <span
                  style={{
                    fontFamily: "var(--serif)",
                    fontVariantNumeric: "tabular-nums",
                    fontWeight: 600,
                    fontSize: 48,
                    lineHeight: 1,
                    letterSpacing: "-1px",
                    color: scoreColor(report.metros[0].scores.opportunity),
                  }}
                >
                  {Math.round(report.metros[0].scores.opportunity)}
                </span>
                <div style={{ width: 120, paddingBottom: 8 }}>
                  <div
                    style={{
                      height: 4,
                      background: scoreBarBg(report.metros[0].scores.opportunity),
                      borderRadius: 2,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${Math.min(report.metros[0].scores.opportunity, 100)}%`,
                        background: scoreColor(report.metros[0].scores.opportunity),
                        borderRadius: 2,
                      }}
                    />
                  </div>
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

          {/* Keywords */}
          {keywords && keywords.length > 0 && (
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
                Keyword expansion ({keywords.length})
              </h3>
              <KeywordTable keywords={keywords} />
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
