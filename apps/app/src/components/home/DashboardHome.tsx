import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import { Icon, I } from "@/lib/icons";
import type { DashboardData } from "@/lib/home/load-dashboard";
import NextMoveCard from "@/components/NextMoveCard";

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function Card({
  children,
  ariaLabelledBy,
  style,
}: {
  children: ReactNode;
  ariaLabelledBy?: string;
  style?: CSSProperties;
}) {
  return (
    <section
      aria-labelledby={ariaLabelledBy}
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: 18,
        boxShadow: "0 1px 0 rgba(47,38,20,0.03)",
        ...style,
      }}
    >
      {children}
    </section>
  );
}

function ActionLink({
  href,
  children,
  variant = "primary",
  ariaLabel,
}: {
  href: string;
  children: ReactNode;
  variant?: "primary" | "ghost";
  ariaLabel?: string;
}) {
  return (
    <Link
      href={href}
      className={variant === "primary" ? "btn-primary" : "btn-ghost"}
      style={{ justifyContent: "center", textDecoration: "none", whiteSpace: "normal" }}
      aria-label={ariaLabel}
    >
      {children}
    </Link>
  );
}

function AccountErrorCard({ dashboard }: { dashboard: DashboardData }) {
  const message =
    dashboard.account.status === "error"
      ? dashboard.account.error.message
      : "Account details are unavailable.";

  return (
    <Card>
      <div role="alert" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div>
          <p
            style={{
              margin: 0,
              color: "var(--danger)",
              fontSize: 12,
              fontWeight: 700,
              textTransform: "uppercase",
            }}
          >
            Account needs attention
          </p>
          <h1 className="page-h1" style={{ margin: "6px 0 0" }}>
            We could not load your dashboard entitlement.
          </h1>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            {message}
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <ActionLink href="/settings">
            Open settings <Icon d={I.arrow} />
          </ActionLink>
          <ActionLink href="/explore" variant="ghost">
            Explore cached reports
          </ActionLink>
        </div>
      </div>
    </Card>
  );
}

function AccountWarningNotice({ dashboard }: { dashboard: DashboardData }) {
  if (dashboard.account.status !== "error" || dashboard.account.blocking) return null;

  return (
    <div
      role="status"
      aria-label="Account warning"
      style={{
        border: "1px solid var(--warn)",
        borderRadius: 8,
        background: "var(--warn-soft)",
        color: "var(--ink)",
        padding: "10px 12px",
        fontSize: 13,
      }}
    >
      <strong>Account usage is temporarily unavailable.</strong>{" "}
      <span style={{ color: "var(--ink-2)" }}>{dashboard.account.error.message}</span>{" "}
      <Link href="/settings" className="settings-link">
        Manage
      </Link>
    </div>
  );
}

function FindFirstStarterHero({ dashboard }: { dashboard: DashboardData }) {
  if (dashboard.onboarding.next_route !== "/") return null;
  const starter =
    dashboard.strategies.catalog.strategies.find(
      (strategy) => strategy.strategy_id === "easy_win",
    ) ?? (dashboard.strategies.starter.strategy_id === "easy_win" ? dashboard.strategies.starter : null);
  if (!starter) return null;
  const canRunFresh = dashboard.account.can_run_fresh_reports;
  const primaryHref = canRunFresh ? `/strategies/${starter.strategy_id}` : "/explore";
  const account = dashboard.account.status === "ready" ? dashboard.account : null;
  const isFree = account?.entitlement.plan_key === "free";
  const hasUsedScan = (account?.summary.fresh_reports_used ?? 0) > 0;
  const secondaryHref = canRunFresh ? "/strategies" : "/settings";
  const secondaryLabel = canRunFresh ? "Compare strategy path" : "Review plan";
  const heading = hasUsedScan
    ? `Run another ${starter.name} market check.`
    : `Find your first ${starter.name} market.`;
  const body = canRunFresh
    ? hasUsedScan
      ? `${starter.name} stays your shortest path to another focused market check.`
      : `${starter.name} is ready for a focused city and service scan.`
    : isFree
      ? "Free accounts can browse cached opportunities now and upgrade before spending on fresh scans."
      : "Your fresh scan quota is used for this period. Cached Explore stays available while quota resets.";

  return (
    <Card
      style={{
        border: "2px solid var(--accent)",
        borderLeft: "6px solid var(--accent)",
        background: "var(--card)",
        padding: 0,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "start",
          gap: 16,
          padding: 20,
        }}
      >
        <div
          aria-hidden="true"
          style={{
            width: 42,
            height: 42,
            borderRadius: "50%",
            background: "var(--accent)",
            color: "white",
            display: "grid",
            placeItems: "center",
            boxShadow: "0 0 0 6px rgba(15,122,87,0.14)",
          }}
        >
          <Icon d={I.star} size={20} fill="currentColor" sw={1.2} />
        </div>
        <div style={{ flex: "1 1 360px", maxWidth: 760, minWidth: 0 }}>
          <p
            style={{
              margin: 0,
              color: "var(--accent-ink)",
              fontSize: 12,
              fontWeight: 700,
              textTransform: "uppercase",
            }}
          >
            Find first
          </p>
          <h2
            style={{
              margin: "6px 0 0",
              color: "var(--ink)",
              fontFamily: "var(--serif)",
              fontSize: 24,
              fontWeight: 400,
              lineHeight: 1.15,
            }}
          >
            {heading}
          </h2>
          <p style={{ margin: "8px 0 0", color: "var(--ink-2)", fontSize: 13.5, lineHeight: 1.5 }}>
            {body}
          </p>
          <ol
            style={{
              margin: "14px 0 0",
              padding: 0,
              listStyle: "none",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
              gap: 10,
            }}
          >
            {[
              `Start with ${starter.name}`,
              "Confirm city and service",
              "Review the scored report",
            ].map((step, index) => (
              <li
                key={step}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  color: "var(--ink-2)",
                  fontSize: 12.5,
                }}
              >
                <span
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: "50%",
                    background: index === 0 ? "var(--accent)" : "var(--card)",
                    border: "1px solid var(--rule-strong)",
                    color: index === 0 ? "white" : "var(--ink-2)",
                    display: "grid",
                    placeItems: "center",
                    fontFamily: "var(--mono)",
                    fontSize: 11,
                    fontWeight: 700,
                    flex: "0 0 auto",
                  }}
                >
                  {index + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </div>
        <div style={{ display: "flex", flex: "1 1 210px", flexDirection: "column", gap: 10, alignItems: "stretch", maxWidth: 260 }}>
          <ActionLink href={primaryHref} ariaLabel="Start first dashboard action">
            {canRunFresh ? `Start ${starter.name}` : "Explore cached reports"} <Icon d={I.arrow} />
          </ActionLink>
          <ActionLink href={secondaryHref} variant="ghost">
            {secondaryLabel}
          </ActionLink>
        </div>
      </div>
    </Card>
  );
}

function UsageStrip({ dashboard }: { dashboard: DashboardData }) {
  const account = dashboard.account.status === "ready" ? dashboard.account : null;
  const scansRemaining = account
    ? account.entitlement.fresh_report_quota_exempt
      ? "Unlimited"
      : `${formatNumber(account.summary.fresh_reports_remaining)} / ${formatNumber(
          account.summary.monthly_report_limit,
        )}`
    : "Unavailable";
  const plan = account?.summary.plan_label ?? "Unavailable";
  const reportCount = formatNumber(dashboard.stats.total_reports);
  const lens = dashboard.strategies.starter.name;
  const values = [
    { label: "Scans remaining", value: scansRemaining, link: null },
    { label: "Current plan", value: plan, link: { href: "/settings", label: "Manage" } },
    { label: "Reports", value: reportCount, link: { href: "/reports", label: "View all" } },
    { label: "Current lens", value: lens, link: { href: "/strategies", label: "Change" } },
  ];

  return (
    <section aria-label="Dashboard usage" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
      {values.map((item) => (
        <div
          key={item.label}
          style={{
            background: "var(--card)",
            border: "1px solid var(--rule)",
            borderRadius: 8,
            padding: "14px 16px",
            minWidth: 0,
          }}
        >
          <div style={{ color: "var(--ink-3)", fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
            {item.label}
          </div>
          <div
            style={{
              marginTop: 7,
              color: "var(--ink)",
              fontFamily: "var(--serif)",
              fontSize: 24,
              fontWeight: 400,
              lineHeight: 1.1,
              overflowWrap: "anywhere",
            }}
          >
            {item.value}
          </div>
          {item.link ? (
            <Link href={item.link.href} className="settings-link" style={{ display: "inline-flex", marginTop: 8 }}>
              {item.link.label}
            </Link>
          ) : null}
        </div>
      ))}
    </section>
  );
}

function ScalePortfolioGlance({ dashboard }: { dashboard: DashboardData }) {
  if (dashboard.onboarding.next_route !== "/strategies") return null;
  const latest = dashboard.recent.at(0);
  const statusRows = [
    {
      label: "Markets reviewed",
      value: formatNumber(dashboard.stats.total_reports),
    },
    {
      label: "Average score",
      value: dashboard.stats.total_reports > 0 ? formatNumber(dashboard.stats.avg_score) : "No scores yet",
    },
    {
      label: "Latest report",
      value: latest ? `${latest.city} · ${latest.niche}` : "No recent reports",
    },
  ];

  return (
    <Card ariaLabelledBy="portfolio-glance-heading">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 18, alignItems: "stretch" }}>
        <div style={{ minWidth: 0 }}>
          <p style={{ margin: 0, color: "var(--accent-ink)", fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
            Scale
          </p>
          <h2
            id="portfolio-glance-heading"
            style={{
              margin: "6px 0 0",
              color: "var(--ink)",
              fontFamily: "var(--serif)",
              fontSize: 26,
              fontWeight: 400,
              lineHeight: 1.12,
            }}
          >
            Portfolio status
          </h2>
          <p style={{ margin: "8px 0 0", color: "var(--ink-2)", fontSize: 13.5, lineHeight: 1.5 }}>
            Use the strategy path to compare your next market, then return here to track recent reports.
          </p>
          <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10 }}>
            {statusRows.map((row) => (
              <div
                key={row.label}
                style={{
                  border: "1px solid var(--rule)",
                  borderRadius: 8,
                  background: "var(--paper)",
                  padding: 12,
                  minWidth: 0,
                }}
              >
                <div style={{ color: "var(--ink-3)", fontSize: 11, fontWeight: 700, textTransform: "uppercase" }}>
                  {row.label}
                </div>
                <div style={{ marginTop: 6, color: "var(--ink)", fontSize: 15, fontWeight: 700, overflowWrap: "anywhere" }}>
                  {row.value}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, justifyContent: "center" }}>
          <ActionLink href="/strategies" ariaLabel="Open portfolio builder">
            Open portfolio builder <Icon d={I.arrow} />
          </ActionLink>
          <ActionLink href={latest ? `/reports?open=${encodeURIComponent(latest.id)}` : "/reports"} variant="ghost">
            {latest ? "Review latest report" : "Open reports"}
          </ActionLink>
        </div>
      </div>
    </Card>
  );
}

function SegmentFirstSurfaceCard({ dashboard }: { dashboard: DashboardData }) {
  const route = dashboard.onboarding.next_route;
  if (route === "/" || route === "/strategies") {
    return null;
  }

  const agencyAvailable = dashboard.multi_market_available;
  const surface = route === "/agency"
    ? agencyAvailable
      ? {
          eyebrow: "Coach and agency",
          heading: "Start in the agency workspace.",
          body: "Qualify territories in one batch and keep the dashboard as a status surface.",
          primaryHref: "/agency",
          primaryLabel: "Open agency workspace",
          secondaryHref: "/reports",
          secondaryLabel: "Review reports",
        }
      : {
          eyebrow: "Coach and agency",
          heading: "Agency workspace is not available yet.",
          body: "Use reports and cached research while batch territory tooling is unavailable.",
          primaryHref: "/reports",
          primaryLabel: "Review reports",
          secondaryHref: "/explore",
          secondaryLabel: "Open Explore",
        }
    : route === "/explore"
      ? {
          eyebrow: "Researching",
          heading: "Start with cached market research.",
          body: "Browse existing opportunities without spending a fresh scan, then promote only the markets worth testing.",
          primaryHref: "/explore",
          primaryLabel: "Open Explore",
          secondaryHref: "/strategies",
          secondaryLabel: "Compare strategies",
        }
      : null;

  if (!surface) return null;

  return (
    <Card ariaLabelledBy="segment-first-surface-heading">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 18, flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 360px", minWidth: 0 }}>
          <p style={{ margin: 0, color: "var(--accent-ink)", fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
            {surface.eyebrow}
          </p>
          <h2
            id="segment-first-surface-heading"
            style={{
              margin: "6px 0 0",
              color: "var(--ink)",
              fontFamily: "var(--serif)",
              fontSize: 24,
              fontWeight: 400,
              lineHeight: 1.15,
            }}
          >
            {surface.heading}
          </h2>
          <p style={{ margin: "8px 0 0", color: "var(--ink-2)", fontSize: 13.5, lineHeight: 1.5 }}>
            {surface.body}
          </p>
        </div>
        <div style={{ display: "flex", flex: "1 1 220px", flexDirection: "column", gap: 10, maxWidth: 280 }}>
          <ActionLink href={surface.primaryHref} ariaLabel={surface.primaryLabel}>
            {surface.primaryLabel} <Icon d={I.arrow} />
          </ActionLink>
          <ActionLink href={surface.secondaryHref} variant="ghost">
            {surface.secondaryLabel}
          </ActionLink>
        </div>
      </div>
    </Card>
  );
}

function SecondaryCards({ dashboard }: { dashboard: DashboardData }) {
  const showAgencyCard = dashboard.onboarding.next_route === "/agency";

  return (
    <section aria-label="Dashboard destinations" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 14 }}>
      <NextMoveCard
        href="/explore"
        title="Explore cached data"
        subtitle="Browse for free. No scans consumed."
        ctaLabel="Open Explore"
      />

      {showAgencyCard && dashboard.multi_market_available ? (
        <NextMoveCard
          href="/agency"
          title="Agency workspace"
          subtitle="Batch territory checks for coaching and agency workflows."
          ctaLabel="Open agency workspace"
        />
      ) : showAgencyCard ? (
        <Card ariaLabelledBy="multi-market-card-heading">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <h2 id="multi-market-card-heading" style={{ margin: 0, color: "var(--ink)", fontFamily: "var(--serif)", fontSize: 20, fontWeight: 400 }}>
                Agency workspace
              </h2>
              <p style={{ margin: "7px 0 0", color: "var(--ink-2)", fontSize: 13.5, lineHeight: 1.5, fontStyle: "italic" }}>
                Batch territory checks for coaching and agency workflows.
              </p>
            </div>
            <span
              aria-disabled="true"
              style={{
                alignSelf: "flex-start",
                border: "1px solid var(--rule-strong)",
                borderRadius: 7,
                color: "var(--ink-3)",
                background: "var(--paper-alt)",
                fontSize: 12,
                fontWeight: 700,
                padding: "8px 12px",
              }}
            >
              Coming soon
            </span>
          </div>
        </Card>
      ) : null}
    </section>
  );
}

function StrategyShortcuts({ dashboard }: { dashboard: DashboardData }) {
  return (
    <Card ariaLabelledBy="strategy-shortcuts-heading">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12, marginBottom: 12 }}>
        <h2 id="strategy-shortcuts-heading" style={{ margin: 0, color: "var(--ink)", fontFamily: "var(--serif)", fontSize: 20, fontWeight: 400 }}>
          Your strategy shortcuts
        </h2>
        <Link href="/strategies" className="settings-link">
          See all <Icon d={I.arrow} />
        </Link>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 12 }}>
        {dashboard.strategies.shortcuts.map((strategy) => (
          <Link
            key={strategy.strategy_id}
            href={`/strategies/${strategy.strategy_id}`}
            style={{
              border: "1px solid var(--rule)",
              borderRadius: 8,
              background: "var(--paper)",
              padding: 14,
              color: "inherit",
              textDecoration: "none",
              minHeight: 138,
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            <span style={{ color: "var(--ink)", fontWeight: 700 }}>{strategy.name}</span>
            <span style={{ color: "var(--ink-2)", fontSize: 13, lineHeight: 1.45 }}>
              {strategy.description}
            </span>
            <span style={{ marginTop: "auto", color: "var(--accent-ink)", fontSize: 12, fontWeight: 700 }}>
              Open lens
            </span>
          </Link>
        ))}
      </div>
    </Card>
  );
}

function RecentReports({ dashboard }: { dashboard: DashboardData }) {
  return (
    <Card ariaLabelledBy="recent-reports-heading">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12, marginBottom: 12 }}>
        <h2 id="recent-reports-heading" style={{ margin: 0, color: "var(--ink)", fontFamily: "var(--serif)", fontSize: 20, fontWeight: 400 }}>
          Recent reports
        </h2>
        <Link href="/reports" className="settings-link">
          View all
        </Link>
      </div>
      {dashboard.recent.length === 0 ? (
        <p style={{ margin: 0, color: "var(--ink-2)", fontSize: 13.5 }}>
          No recent reports yet.
        </p>
      ) : (
        <div className="results" style={{ borderRadius: 8 }}>
          {dashboard.recent.map((item) => (
            <Link
              key={item.id}
              href={`/reports?open=${encodeURIComponent(item.id)}`}
              className="res-row report-row-clickable"
              style={{
                gridTemplateColumns: "minmax(0, 1fr) auto auto",
                textDecoration: "none",
                color: "inherit",
              }}
            >
              <span style={{ minWidth: 0 }}>
                <span className="res-metro">{item.city}</span>
                <span className="res-metro-sub">{item.niche}</span>
              </span>
              <span style={{ color: "var(--ink-3)", fontFamily: "var(--mono)", fontSize: 12 }}>
                {formatDate(item.created_at)}
              </span>
              <span className="res-open" aria-hidden="true">
                <Icon d={I.arrow} />
              </span>
            </Link>
          ))}
        </div>
      )}
    </Card>
  );
}

function ReportErrorNotice({ dashboard }: { dashboard: DashboardData }) {
  if (!dashboard.report_error) return null;

  return (
    <div
      role="status"
      style={{
        border: "1px solid var(--warn)",
        borderRadius: 8,
        background: "var(--warn-soft)",
        color: "var(--ink)",
        padding: "10px 12px",
        fontSize: 13,
      }}
    >
      <strong>Reports are temporarily unavailable.</strong>{" "}
      <span style={{ color: "var(--ink-2)" }}>{dashboard.report_error.message}</span>
    </div>
  );
}

export default function DashboardHome({ dashboard }: { dashboard: DashboardData }) {
  return (
    <main
      className="page"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 18,
        maxWidth: 1280,
        margin: "0 auto",
        width: "100%",
      }}
    >
      {dashboard.account.status === "error" && dashboard.account.blocking ? (
        <AccountErrorCard dashboard={dashboard} />
      ) : (
        <>
          <header>
            <h1 className="page-h1" style={{ margin: 0 }}>
              Dashboard
            </h1>
            <p className="page-sub" style={{ marginBottom: 0 }}>
              Strategy-first market discovery for launch-safe scans and cached opportunities.
            </p>
          </header>

          <AccountWarningNotice dashboard={dashboard} />
          <ReportErrorNotice dashboard={dashboard} />
          <FindFirstStarterHero dashboard={dashboard} />
          <UsageStrip dashboard={dashboard} />
          <ScalePortfolioGlance dashboard={dashboard} />
          <SegmentFirstSurfaceCard dashboard={dashboard} />
          <SecondaryCards dashboard={dashboard} />
          <StrategyShortcuts dashboard={dashboard} />
          <RecentReports dashboard={dashboard} />
        </>
      )}
    </main>
  );
}
