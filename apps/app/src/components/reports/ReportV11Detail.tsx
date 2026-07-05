import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import { AIResilienceFlagBadge } from "@/components/AIResilienceFlagBadge";
import Term from "@/components/glossary/Term";
import { ScoreBar } from "@/components/ScoreVisuals";
import { StrategyResultSummary } from "@/components/strategies/StrategyResultSummary";
import { ARCHETYPES } from "@/lib/archetypes";
import { scoreToneForValue } from "@/lib/design-tokens";
import { Icon, I } from "@/lib/icons";
import type { FullReportData, MetroScores, ReportMetro } from "@/lib/niche-finder/types";
import type { ScoreKey } from "@/lib/reports/score-explainers";
import {
  buildReportNextSteps,
  type ReportNextStep,
  type ReportNextStepContext,
} from "@/lib/reports/report-next-steps";
import {
  createReportStrategyResultSummary,
  normalizeReportGuidanceEvidence,
  userFacingStrategyProfileLabel,
} from "@/lib/strategy-result-summary";
import ScoreBreakdownTabs from "@/components/reports/ScoreBreakdownTabs";
import ScoreInfoHover from "@/components/reports/ScoreInfoHover";

type ReportV11Variant = "page" | "modal";

interface ReportV11DetailProps {
  report: FullReportData;
  variant?: ReportV11Variant;
  actions?: ReactNode;
  headerAccessory?: ReactNode;
  showBackLink?: boolean;
  primaryReportHref?: string | null;
  reportCtaLabel?: string;
  nextStepContext?: ReportNextStepContext;
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

const REPORT_DEPTH_LABELS: Record<string, string> = {
  standard: "Standard report",
  deep: "Deep report",
};

const SCORE_CELLS = [
  { label: "Demand", scoreKey: "demand" },
  { label: "Organic ease", scoreKey: "organic_competition" },
  { label: "Local ease", scoreKey: "local_competition" },
  { label: "Monetization", scoreKey: "monetization" },
  { label: "AI Resilience", scoreKey: "ai_resilience" },
  { label: "Opportunity", scoreKey: "opportunity" },
] as const satisfies readonly { label: string; scoreKey: ScoreKey }[];

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function humanizeToken(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function enumLabel(value: string, labels: Record<string, string> = {}): string {
  return labels[value] ?? humanizeToken(value);
}

function reportDepthLabel(value: string | null | undefined): string | null {
  if (!value?.trim()) return null;
  const normalized = value.trim().toLowerCase();
  return REPORT_DEPTH_LABELS[normalized] ?? humanizeToken(value);
}

function archetypeLabel(id?: string): { label: string; glyph: string } {
  if (!id) return { label: "Unknown", glyph: "arch-mixed" };
  const normalized = id.toUpperCase().replace(/[\s-]+/g, "_");
  const found = ARCHETYPES.find(
    (archetype) =>
      archetype.id === id ||
      archetype.id === normalized ||
      archetype.title.toUpperCase().replace(/[\s-]+/g, "_") === normalized,
  );
  return found
    ? { label: found.short, glyph: found.glyph }
    : { label: humanizeToken(id), glyph: "arch-mixed" };
}

function hasSignals(signals: ReportMetro["signals"]): signals is Record<string, unknown> {
  return Boolean(signals && Object.keys(signals).length > 0);
}

function breakdownScores(scores: Partial<MetroScores>): MetroScores {
  return {
    demand: scores.demand ?? 0,
    organic_competition: scores.organic_competition ?? 0,
    local_competition: scores.local_competition ?? 0,
    monetization: scores.monetization ?? 0,
    ai_resilience: scores.ai_resilience ?? 0,
    opportunity: scores.opportunity ?? 0,
    confidence: scores.confidence,
  };
}

function sectionHeadingStyle(): CSSProperties {
  return {
    margin: "0 0 12px",
    color: "var(--ink-3)",
    fontFamily: "var(--sans)",
    fontSize: 12,
    fontWeight: 800,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  };
}

function Pill({
  children,
  className,
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        minHeight: 22,
        padding: "2px 10px",
        borderRadius: 999,
        fontSize: 11,
        fontFamily: "var(--sans)",
        fontWeight: 700,
        letterSpacing: "0.02em",
        textTransform: "uppercase",
        color: "var(--ink-2)",
        background: "var(--paper-alt)",
        border: "1px solid var(--rule)",
        lineHeight: 1.35,
        ...style,
      }}
    >
      {children}
    </span>
  );
}

function EmptySection({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        border: "1px dashed var(--rule-strong)",
        borderRadius: 8,
        color: "var(--ink-3)",
        fontSize: 13,
        lineHeight: 1.5,
        padding: 14,
      }}
    >
      {children}
    </div>
  );
}

function ReportHeader({
  report,
  variant,
  actions,
  headerAccessory,
  showBackLink,
}: {
  report: FullReportData;
  variant: ReportV11Variant;
  actions?: ReactNode;
  headerAccessory?: ReactNode;
  showBackLink: boolean;
}) {
  const profileLabel = userFacingStrategyProfileLabel(report.strategy_profile);
  const depthLabel = reportDepthLabel(report.report_depth);
  const title = report.niche_keyword || "Report";
  const headerStyle: CSSProperties =
    variant === "modal"
      ? {
          borderBottom: "1px solid var(--rule)",
          background: "var(--card)",
          borderRadius: "14px 14px 0 0",
          padding: "22px 24px 18px",
          position: "sticky",
          top: 0,
          zIndex: 1,
        }
      : {
          display: "flex",
          justifyContent: "space-between",
          gap: 18,
          alignItems: "flex-start",
          flexWrap: "wrap",
        };

  return (
    <header style={{ ...headerStyle, position: headerStyle.position ?? "relative" }}>
      {headerAccessory}
      <div style={{ minWidth: 0, paddingRight: variant === "modal" ? 42 : 0 }}>
        {showBackLink ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              color: "var(--ink-3)",
              fontSize: 13,
              marginBottom: 10,
            }}
          >
            <Link href="/reports" style={{ color: "inherit", textDecoration: "none" }}>
              Reports
            </Link>
            <span>/</span>
            <span>Report</span>
          </div>
        ) : (
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
        )}

        {variant === "page" ? (
          <h1
            style={{
              fontFamily: "var(--serif)",
              fontSize: 36,
              fontWeight: 600,
              lineHeight: 1.05,
              color: "var(--ink)",
              margin: 0,
              overflowWrap: "anywhere",
            }}
          >
            {title}
          </h1>
        ) : (
          <h2
            style={{
              fontFamily: "var(--serif)",
              fontSize: 24,
              fontWeight: 600,
              letterSpacing: 0,
              color: "var(--ink)",
              margin: 0,
              overflowWrap: "anywhere",
            }}
          >
            {title}
          </h2>
        )}

        <div
          style={{
            fontFamily: "var(--serif)",
            fontStyle: "italic",
            fontSize: 14,
            color: "var(--ink-2)",
            marginTop: variant === "page" ? 8 : 4,
          }}
        >
          {[report.geo_target, formatDate(report.created_at)].filter(Boolean).join(" - ")}
        </div>

        <div style={{ display: "flex", gap: 6, marginTop: 12, flexWrap: "wrap", alignItems: "center" }}>
          {report.spec_version ? <Pill>Report v{report.spec_version}</Pill> : null}
          {profileLabel ? <Pill>{profileLabel}</Pill> : null}
          {depthLabel ? <Pill>{depthLabel}</Pill> : null}
        </div>
      </div>

      {actions ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            flexWrap: "wrap",
            justifyContent: variant === "page" ? "flex-end" : "flex-start",
            marginTop: variant === "modal" ? 12 : 0,
          }}
        >
          {variant === "page" ? (
            <Link href="/reports" className="btn-ghost" style={{ textDecoration: "none" }}>
              Back to reports
            </Link>
          ) : null}
          {actions}
        </div>
      ) : null}
    </header>
  );
}

function ScoreCell({
  label,
  value,
  scoreKey,
}: {
  label: string;
  value: number | undefined;
  scoreKey: ScoreKey;
}) {
  const tone = scoreToneForValue(value);
  return (
    <div style={{ minWidth: 0 }}>
      <div
        style={{
          fontFamily: "var(--mono)",
          fontVariantNumeric: "tabular-nums",
          fontWeight: 800,
          fontSize: 28,
          lineHeight: 1,
          color: tone.text,
        }}
      >
        {value == null ? "-" : Math.round(value)}
      </div>
      <div style={{ marginTop: 7 }}>
        <ScoreBar value={value} label={label} hideLabel hideValue />
      </div>
      <div
        style={{
          marginTop: 8,
          display: "flex",
          alignItems: "center",
          fontFamily: "var(--serif)",
          fontStyle: "italic",
          fontSize: 12,
          color: "var(--ink-3)",
        }}
      >
        {label}
        <ScoreInfoHover scoreKey={scoreKey} />
      </div>
      {scoreKey === "ai_resilience" ? (
        <div style={{ marginTop: 7 }}>
          <AIResilienceFlagBadge score={value} />
        </div>
      ) : null}
    </div>
  );
}

function ScoreGrid({ metro }: { metro: ReportMetro }) {
  const scores = (metro.scores ?? {}) as Partial<MetroScores>;
  return (
    <section
      aria-label="Signal scores"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
        gap: 16,
      }}
    >
      {SCORE_CELLS.map((cell) => (
        <ScoreCell
          key={cell.scoreKey}
          label={cell.label}
          value={scores[cell.scoreKey]}
          scoreKey={cell.scoreKey}
        />
      ))}
    </section>
  );
}

function MetroBadges({ metro }: { metro: ReportMetro }) {
  const scores = (metro.scores ?? {}) as Partial<MetroScores>;
  const archetype = archetypeLabel(metro.serp_archetype);
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 18 }}>
      {metro.population ? <Pill>Pop. {metro.population.toLocaleString("en-US")}</Pill> : null}
      {metro.serp_archetype ? (
        <Pill className={archetype.glyph}>
          <Term termKey="archetype" label="Archetype" />: {archetype.label}
        </Pill>
      ) : null}
      {metro.difficulty_tier ? (
        <Pill>
          <Term termKey="keyword_difficulty" label="KD" />:{" "}
          {enumLabel(metro.difficulty_tier, DIFFICULTY_LABELS)}
        </Pill>
      ) : null}
      {metro.ai_exposure ? (
        <Pill>AI exposure: {enumLabel(metro.ai_exposure, EXPOSURE_LABELS)}</Pill>
      ) : null}
      {scores.confidence ? (
        <Pill>Confidence: {Math.round(scores.confidence.score)}</Pill>
      ) : (
        <Pill>Confidence: Not scored yet</Pill>
      )}
    </div>
  );
}

function SignalsSection({ metro }: { metro: ReportMetro }) {
  const scores = (metro.scores ?? {}) as Partial<MetroScores>;
  if (!hasSignals(metro.signals)) {
    return (
      <section aria-label="Signals" style={{ marginTop: 20 }}>
        <h3 style={sectionHeadingStyle()}>Signals</h3>
        <EmptySection>Signal-level evidence is not available for this report yet.</EmptySection>
      </section>
    );
  }

  return (
    <div style={{ marginTop: 20 }}>
      <ScoreBreakdownTabs signals={metro.signals} scores={breakdownScores(scores)} />
    </div>
  );
}

function EvidenceSection({ metro }: { metro: ReportMetro }) {
  const guidanceEvidence = normalizeReportGuidanceEvidence(metro.guidance);
  const hasEvidence =
    guidanceEvidence.narrative.length > 0 || guidanceEvidence.actionItems.length > 0;

  return (
    <section aria-label="Evidence" style={{ marginTop: 20 }}>
      <h3 style={sectionHeadingStyle()}>Evidence</h3>
      {hasEvidence ? (
        <div
          style={{
            background: "linear-gradient(135deg, #1f1b16, #393124)",
            borderRadius: 8,
            padding: 20,
            color: "#fff",
          }}
        >
          {guidanceEvidence.narrative.map((item, index) => (
            <p
              key={item}
              style={{
                margin:
                  index === guidanceEvidence.narrative.length - 1 &&
                  guidanceEvidence.actionItems.length === 0
                    ? 0
                    : "0 0 14px",
                color: "#eee8dc",
                fontSize: 14,
                lineHeight: 1.6,
              }}
            >
              {item}
            </p>
          ))}
          {guidanceEvidence.actionItems.length > 0 ? (
            <ol
              style={{
                margin: 0,
                paddingLeft: 20,
                display: "grid",
                gap: 8,
                color: "#f7f2e8",
                fontSize: 13.5,
              }}
            >
              {guidanceEvidence.actionItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
          ) : null}
        </div>
      ) : (
        <EmptySection>No narrative evidence is available for this report yet.</EmptySection>
      )}
    </section>
  );
}

function MetroDetailSection({
  report,
  metro,
  primary,
  reportHref,
  reportCtaLabel,
}: {
  report: FullReportData;
  metro: ReportMetro;
  primary?: boolean;
  reportHref?: string | null;
  reportCtaLabel?: string;
}) {
  return (
    <section
      aria-label={primary ? "Score and verdict" : `${metro.cbsa_name} report detail`}
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: primary ? 24 : 20,
      }}
    >
      {primary ? (
        <StrategyResultSummary
          summary={createReportStrategyResultSummary({ report, metro, reportHref })}
          framed={false}
          reportCtaLabel={reportCtaLabel}
        />
      ) : (
        <h2
          style={{
            margin: "0 0 14px",
            fontFamily: "var(--serif)",
            fontSize: 22,
            color: "var(--ink)",
          }}
        >
          {metro.cbsa_name}
        </h2>
      )}

      <div style={{ marginTop: primary ? 20 : 0 }}>
        <ScoreGrid metro={metro} />
        <MetroBadges metro={metro} />
      </div>
      <SignalsSection metro={metro} />
      <EvidenceSection metro={metro} />
    </section>
  );
}

function NextMoveCard({
  step,
}: {
  step: ReportNextStep;
}) {
  const statusLabel =
    step.state === "locked" ? step.requirement_label ?? "Locked" : step.state === "future" ? "Future" : null;
  const content = (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
        <div style={{ fontWeight: 700, fontSize: 14, color: "var(--ink)" }}>{step.title}</div>
        {statusLabel ? (
          <span
            style={{
              border: "1px solid var(--rule)",
              borderRadius: 999,
              color: step.state === "future" ? "var(--ink-3)" : "var(--warn)",
              background: step.state === "future" ? "var(--paper-alt)" : "var(--warn-soft)",
              fontSize: 10.5,
              fontWeight: 800,
              letterSpacing: "0.02em",
              padding: "3px 7px",
              textTransform: "uppercase",
              whiteSpace: "nowrap",
            }}
          >
            {statusLabel}
          </span>
        ) : null}
      </div>
      <div style={{ marginTop: 4, fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.45 }}>
        {step.subtitle}
      </div>
      <div
        style={{
          marginTop: 12,
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          color: step.href ? "var(--accent)" : "var(--ink-3)",
          fontSize: 12,
          fontWeight: 700,
        }}
      >
        {step.cta_label ?? (step.href ? "Continue" : "Locked")}
        {step.href ? <Icon d={I.arrow} /> : null}
      </div>
    </>
  );
  const cardStyle: CSSProperties = {
    display: "block",
    padding: 16,
    borderRadius: 8,
    border: step.primary ? "1px solid var(--ink)" : "1px solid var(--rule)",
    background: step.href ? "var(--card)" : "var(--paper-alt)",
    color: "inherit",
    textDecoration: "none",
    minHeight: 144,
  };

  if (!step.href) {
    return (
      <article style={cardStyle}>
        {content}
      </article>
    );
  }

  return (
    <Link href={step.href} style={cardStyle}>
      {content}
    </Link>
  );
}

function NextMoves({
  report,
  metro,
  context,
}: {
  report: FullReportData;
  metro: ReportMetro;
  context?: ReportNextStepContext;
}) {
  const nextSteps = buildReportNextSteps({ report, metro, context });
  return (
    <section aria-label="Next steps">
      <h2 style={sectionHeadingStyle()}>Next steps</h2>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 12,
        }}
      >
        {nextSteps.map((step) => (
          <NextMoveCard key={step.id} step={step} />
        ))}
      </div>
    </section>
  );
}

function MetaSection({ meta }: { meta: FullReportData["meta"] }) {
  if (!meta || Object.keys(meta).length === 0) return null;
  return (
    <details
      style={{
        border: "1px solid var(--rule)",
        borderRadius: 8,
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
        Source context
      </summary>
      <div
        style={{
          padding: "0 14px 14px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: "10px 16px",
        }}
      >
        {meta.processing_time_seconds != null ? (
          <MetaItem label="Processing time" value={`${Number(meta.processing_time_seconds).toFixed(1)}s`} />
        ) : null}
        {meta.total_api_calls != null ? (
          <MetaItem label="API calls" value={String(meta.total_api_calls)} />
        ) : null}
        {meta.total_cost_usd != null ? (
          <MetaItem label="Cost" value={`$${Number(meta.total_cost_usd).toFixed(4)}`} />
        ) : null}
      </div>
    </details>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 11, color: "var(--ink-3)" }}>
        {label}
      </div>
      <div style={{ fontFamily: "var(--mono)", fontSize: 13, color: "var(--ink)" }}>{value}</div>
    </div>
  );
}

function ReportV11Content(props: ReportV11DetailProps & { variant: ReportV11Variant }) {
  const {
    report,
    variant,
    actions,
    headerAccessory,
    showBackLink = variant === "page",
    primaryReportHref = variant === "page" ? null : undefined,
    reportCtaLabel = variant === "modal" ? "Open full report page" : "Open full report",
    nextStepContext,
  } = props;
  const metros = Array.isArray(report.metros) ? report.metros : [];
  const topMetro = metros[0];
  const bodyPadding = variant === "modal" ? "20px 24px 28px" : 0;

  return (
    <>
      <ReportHeader
        report={report}
        variant={variant}
        actions={actions}
        headerAccessory={headerAccessory}
        showBackLink={showBackLink}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 24,
          padding: bodyPadding,
        }}
      >
        {topMetro ? (
          <>
            <MetroDetailSection
              report={report}
              metro={topMetro}
              primary
              reportHref={primaryReportHref}
              reportCtaLabel={reportCtaLabel}
            />
            <NextMoves report={report} metro={topMetro} context={nextStepContext} />
            {metros.slice(1).map((metro) => (
              <MetroDetailSection key={metro.cbsa_code || metro.cbsa_name} report={report} metro={metro} />
            ))}
          </>
        ) : (
          <section
            style={{
              background: "var(--card)",
              border: "1px solid var(--rule)",
              borderRadius: 8,
              padding: 24,
              color: "var(--ink-2)",
            }}
          >
            This report does not include metro score data yet.
          </section>
        )}
        <MetaSection meta={report.meta} />
      </div>
    </>
  );
}

export default function ReportV11Detail({
  variant = "page",
  ...props
}: ReportV11DetailProps) {
  if (variant === "modal") {
    return (
      <div>
        <ReportV11Content {...props} variant="modal" />
      </div>
    );
  }

  return (
    <main
      className="page"
      style={{
        maxWidth: 1080,
        margin: "0 auto",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 24,
      }}
    >
      <ReportV11Content {...props} variant="page" />
    </main>
  );
}
