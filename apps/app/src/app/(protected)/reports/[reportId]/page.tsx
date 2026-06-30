import Link from "next/link";
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import { Icon, I } from "@/lib/icons";
import { AIResilienceFlagBadge } from "@/components/AIResilienceFlagBadge";
import ScoreBreakdownTabs from "@/components/reports/ScoreBreakdownTabs";
import ScoreInfoHover from "@/components/reports/ScoreInfoHover";
import ReportActions from "@/components/reports/ReportActions";
import type { FullReportData, ReportMetro } from "@/lib/niche-finder/types";
import type { ScoreKey } from "@/lib/reports/score-explainers";

export const dynamic = "force-dynamic";

const APP_BASE_ENV_KEYS = [
  "WIDBY_APP_BASE_URL",
  "NEXT_PUBLIC_APP_URL",
  "NEXT_PUBLIC_SITE_URL",
] as const;

type HeaderReader = {
  get(name: string): string | null;
};

function normalizeAppBaseUrl(baseUrl: string) {
  const trimmed = baseUrl.trim().replace(/\/$/, "");
  if (!trimmed) return "";
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  return `https://${trimmed}`;
}

function getAppRouteUrl(path: string, headerStore: HeaderReader): string | null {
  for (const key of APP_BASE_ENV_KEYS) {
    const configured = process.env[key]?.trim();
    if (configured) return `${normalizeAppBaseUrl(configured)}${path}`;
  }

  const vercelUrl = process.env.VERCEL_URL?.trim();
  if (vercelUrl) return `${normalizeAppBaseUrl(vercelUrl)}${path}`;

  const host = headerStore.get("host")?.trim();
  if (!host) return null;

  try {
    const parsed = new URL(`http://${host}`);
    const hostname = parsed.hostname.replace(/^\[|\]$/g, "");
    const isLocalHost =
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname === "::1";
    if (!isLocalHost) return null;

    const proto = headerStore.get("x-forwarded-proto") === "https" ? "https" : "http";
    return `${proto}://${parsed.host}${path}`;
  } catch {
    return null;
  }
}

function isAbsoluteHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

async function loadReport(reportId: string): Promise<FullReportData | null> {
  const headerStore = await headers();
  const cookie = headerStore.get("cookie") ?? undefined;
  const url = getAppRouteUrl(
    `/api/agent/reports/${encodeURIComponent(reportId)}`,
    headerStore,
  );
  if (!url || !isAbsoluteHttpUrl(url)) return null;

  const response = await fetch(url, {
    cache: "no-store",
    ...(cookie ? { headers: { cookie } } : {}),
  });

  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`report detail: HTTP ${response.status}`);
  }

  const body = (await response.json()) as {
    status?: string;
    message?: string;
    report?: FullReportData;
  };

  if (body.status !== "success" || !body.report) {
    throw new Error(`report detail: ${body.message ?? "invalid response"}`);
  }

  return {
    ...body.report,
    metros: Array.isArray(body.report.metros) ? body.report.metros : [],
    resolved_weights: body.report.resolved_weights as Record<string, number> | null,
    meta: body.report.meta as Record<string, unknown> | null,
  };
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

function humanizeEnum(raw: string): string {
  return raw
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/^\w/, (c) => c.toUpperCase());
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 9px",
        borderRadius: 999,
        fontSize: 11,
        fontFamily: "var(--sans)",
        fontWeight: 700,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
        color: "var(--ink-2)",
        background: "var(--paper-alt)",
        border: "1px solid var(--rule)",
      }}
    >
      {children}
    </span>
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
  const score = value ?? 0;
  return (
    <div>
      <div
        style={{
          fontFamily: "var(--mono)",
          fontVariantNumeric: "tabular-nums",
          fontWeight: 800,
          fontSize: 30,
          lineHeight: 1,
          color: value == null ? "var(--ink-3)" : scoreColor(score),
        }}
      >
        {value == null ? "—" : Math.round(score)}
      </div>
      <div
        style={{
          height: 4,
          marginTop: 7,
          borderRadius: 4,
          background: scoreBarBg(score),
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${Math.min(score, 100)}%`,
            height: "100%",
            borderRadius: 4,
            background: scoreColor(score),
          }}
        />
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

function HeadlineScores({ metro }: { metro: ReportMetro }) {
  const cells = [
    { label: "Demand", value: metro.scores.demand, scoreKey: "demand" as const },
    {
      label: "Organic ease",
      value: metro.scores.organic_competition,
      scoreKey: "organic_competition" as const,
    },
    {
      label: "Local ease",
      value: metro.scores.local_competition,
      scoreKey: "local_competition" as const,
    },
    {
      label: "Monetization",
      value: metro.scores.monetization,
      scoreKey: "monetization" as const,
    },
    {
      label: "AI resilience",
      value: metro.scores.ai_resilience,
      scoreKey: "ai_resilience" as const,
    },
    {
      label: "Opportunity",
      value: metro.scores.opportunity,
      scoreKey: "opportunity" as const,
    },
  ];

  return (
    <section
      aria-label="Headline scores"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
        gap: 16,
      }}
    >
      {cells.map((cell) => (
        <ScoreCell key={cell.label} {...cell} />
      ))}
    </section>
  );
}

function StrategyGuidance({ metro }: { metro: ReportMetro }) {
  if (!metro.guidance?.summary && !metro.guidance?.action_items?.length) {
    return null;
  }

  return (
    <section
      style={{
        background: "linear-gradient(135deg, #1f1b16, #393124)",
        borderRadius: 8,
        padding: 24,
        color: "#fff",
      }}
    >
      <div
        style={{
          color: "#b9e4c9",
          fontFamily: "var(--sans)",
          fontSize: 11,
          fontWeight: 800,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: 8,
        }}
      >
        Strategy guidance
      </div>
      <h2 style={{ fontFamily: "var(--serif)", fontSize: 25, margin: "0 0 10px" }}>
        {metro.cbsa_name}
      </h2>
      {metro.guidance.summary ? (
        <p style={{ margin: "0 0 16px", color: "#eee8dc", fontSize: 14, lineHeight: 1.6, maxWidth: 760 }}>
          {metro.guidance.summary}
        </p>
      ) : null}
      {metro.guidance.action_items?.length ? (
        <ol style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 8, color: "#f7f2e8", fontSize: 13.5 }}>
          {metro.guidance.action_items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}

function NextMoves({ report, metro }: { report: FullReportData; metro: ReportMetro }) {
  const service = encodeURIComponent(report.niche_keyword);
  const city = encodeURIComponent(report.geo_target || metro.cbsa_name);
  const moves = [
    {
      href: `/competitor-intel?city=${city}&service=${service}`,
      title: "Run Competitor Intel",
      subtitle: "Inspect the organic and local operators shaping this market.",
      primary: true,
    },
    {
      href: "/strategies/cash_cow",
      title: "Check economics",
      subtitle: "Pressure-test monetization and lead value with the cash cow lens.",
      primary: false,
    },
    {
      href: "/strategies/expand_conquer",
      title: "Find lookalike cities",
      subtitle: "Use the expansion lens on this market pattern.",
      primary: false,
    },
  ];

  return (
    <section>
      <h2
        style={{
          margin: "0 0 12px",
          color: "var(--ink-3)",
          fontFamily: "var(--sans)",
          fontSize: 12,
          fontWeight: 800,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        Next moves
      </h2>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 12,
        }}
      >
        {moves.map((move) => (
          <Link
            key={move.title}
            href={move.href}
            style={{
              display: "block",
              padding: 16,
              borderRadius: 8,
              border: move.primary ? "1px solid var(--ink)" : "1px solid var(--rule)",
              background: "var(--card)",
              color: "inherit",
              textDecoration: "none",
            }}
          >
            <div style={{ fontWeight: 700, fontSize: 14, color: "var(--ink)" }}>
              {move.title}
            </div>
            <div style={{ marginTop: 4, fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.45 }}>
              {move.subtitle}
            </div>
            <div
              style={{
                marginTop: 12,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                color: "var(--accent)",
                fontSize: 12,
                fontWeight: 700,
              }}
            >
              Continue <Icon d={I.arrow} />
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

function MetroBadges({ metro }: { metro: ReportMetro }) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 18 }}>
      {metro.difficulty_tier ? <Pill>Difficulty: {humanizeEnum(metro.difficulty_tier)}</Pill> : null}
      {metro.ai_exposure ? <Pill>AI exposure: {humanizeEnum(metro.ai_exposure)}</Pill> : null}
      {metro.scores.confidence ? <Pill>Confidence: {metro.scores.confidence.score}</Pill> : null}
    </div>
  );
}

function PrimaryMetroSection({ metro }: { metro: ReportMetro }) {
  return (
    <section
      aria-label="Primary report opportunity"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: 24,
      }}
    >
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 20 }}>
        <div>
          <div
            style={{
              color: "var(--accent-ink)",
              fontFamily: "var(--sans)",
              fontSize: 11,
              fontWeight: 800,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: 6,
            }}
          >
            Top market
          </div>
          <h2 style={{ margin: 0, fontFamily: "var(--serif)", fontSize: 28, color: "var(--ink)" }}>
            {metro.cbsa_name}
          </h2>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginLeft: "auto" }}>
          {metro.population ? <Pill>Pop. {metro.population.toLocaleString("en-US")}</Pill> : null}
          {metro.serp_archetype ? <Pill>{humanizeEnum(metro.serp_archetype)}</Pill> : null}
        </div>
      </div>

      <HeadlineScores metro={metro} />
      <MetroBadges metro={metro} />
      {metro.signals && Object.keys(metro.signals).length > 0 ? (
        <div style={{ marginTop: 20 }}>
          <ScoreBreakdownTabs signals={metro.signals} scores={metro.scores} />
        </div>
      ) : null}
    </section>
  );
}

function MetroSection({ metro }: { metro: ReportMetro }) {
  return (
    <section
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: 20,
      }}
    >
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 18 }}>
        <h2 style={{ margin: 0, fontFamily: "var(--serif)", fontSize: 22, color: "var(--ink)" }}>
          {metro.cbsa_name}
        </h2>
        {metro.population ? <Pill>Pop. {metro.population.toLocaleString("en-US")}</Pill> : null}
        {metro.serp_archetype ? <Pill>{humanizeEnum(metro.serp_archetype)}</Pill> : null}
      </div>
      <HeadlineScores metro={metro} />
      <MetroBadges metro={metro} />
      {metro.signals && Object.keys(metro.signals).length > 0 ? (
        <div style={{ marginTop: 20 }}>
          <ScoreBreakdownTabs signals={metro.signals} scores={metro.scores} />
        </div>
      ) : null}
    </section>
  );
}

export default async function ReportDetailPage({
  params,
}: {
  params: Promise<{ reportId: string }>;
}) {
  const { reportId } = await params;
  const report = await loadReport(reportId);
  if (!report) notFound();

  const topMetro = report.metros[0];

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
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 18,
          alignItems: "flex-start",
          flexWrap: "wrap",
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--ink-3)", fontSize: 13, marginBottom: 10 }}>
            <Link href="/reports" style={{ color: "inherit", textDecoration: "none" }}>
              Reports
            </Link>
            <span>/</span>
            <span>Report</span>
          </div>
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
            {report.niche_keyword}
          </h1>
          <p
            style={{
              margin: "8px 0 0",
              color: "var(--ink-2)",
              fontFamily: "var(--serif)",
              fontStyle: "italic",
              fontSize: 14,
            }}
          >
            {report.geo_target} · {formatDate(report.created_at)}
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
            <Pill>v{report.spec_version}</Pill>
            <Pill>{report.strategy_profile}</Pill>
            <Pill>{report.report_depth}</Pill>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <Link href="/reports" className="btn-ghost" style={{ textDecoration: "none" }}>
            Back to reports
          </Link>
          <ReportActions report={report} enableArchiveDelete />
        </div>
      </header>

      {topMetro ? (
        <>
          <PrimaryMetroSection metro={topMetro} />
          <StrategyGuidance metro={topMetro} />
          <NextMoves report={report} metro={topMetro} />
          {report.metros.slice(1).map((metro) => (
            <MetroSection key={metro.cbsa_code} metro={metro} />
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
    </main>
  );
}
