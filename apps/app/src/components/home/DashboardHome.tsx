import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import { Icon, I } from "@/lib/icons";
import type { DashboardData } from "@/lib/home/load-dashboard";
import type { StrategyCatalogEntry } from "@/lib/strategies/types";

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

function inputShapeLabel(strategy: StrategyCatalogEntry) {
  switch (strategy.input_shape) {
    case "city_service_keyword":
      return "City + service + keyword";
    case "reference_city_service":
      return "Reference city + service";
    case "cached_scan":
      return "Cached scan";
    case "city_service":
    default:
      return "City + service";
  }
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

function FirstRunBanner({ dashboard }: { dashboard: DashboardData }) {
  if (dashboard.account.status !== "ready") return null;
  if (dashboard.account.summary.fresh_reports_used !== 0 || dashboard.recent.length > 0) {
    return null;
  }

  const starter = dashboard.strategies.starter;
  const canRunFresh = dashboard.account.can_run_fresh_reports;
  const primaryHref = canRunFresh ? `/strategies/${starter.strategy_id}` : "/explore";

  return (
    <Card
      style={{
        border: "2px solid #8fd6b2",
        borderLeft: "6px solid var(--accent)",
        background: "linear-gradient(90deg, var(--accent-soft), var(--card) 28%)",
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
            Start here
          </p>
          <h2
            style={{
              margin: "6px 0 0",
              color: "var(--ink)",
              fontFamily: "var(--serif)",
              fontSize: 24,
              fontWeight: 600,
              lineHeight: 1.15,
            }}
          >
            Three steps to your first report.
          </h2>
          <p style={{ margin: "8px 0 0", color: "var(--ink-2)", fontSize: 13.5, lineHeight: 1.5 }}>
            {canRunFresh
              ? `Takes about five minutes. ${starter.name} is ready when you are.`
              : "Your account can browse cached opportunities now, and upgrade when fresh scans are needed."}
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
              "Pick your strategy lens",
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
            {canRunFresh ? `Open ${starter.name}` : "Explore cached reports"} <Icon d={I.arrow} />
          </ActionLink>
          {canRunFresh ? (
            <ActionLink href="/explore" variant="ghost">
              Or browse Explore first
            </ActionLink>
          ) : (
            <ActionLink href="/settings" variant="ghost">
              Manage plan
            </ActionLink>
          )}
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
              fontWeight: 600,
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

function RecommendedHero({ dashboard }: { dashboard: DashboardData }) {
  const starter = dashboard.strategies.starter;
  const canRunFresh =
    dashboard.account.status === "ready" && dashboard.account.can_run_fresh_reports;
  const primaryHref = canRunFresh ? `/strategies/${starter.strategy_id}` : "/explore";

  return (
    <section
      aria-labelledby="recommended-strategy-heading"
      style={{
        background: "linear-gradient(135deg, #1f1b16, #343025)",
        border: "1px solid #403a2c",
        borderRadius: 8,
        padding: 22,
        color: "var(--paper)",
        boxShadow: "0 16px 40px rgba(31,27,22,0.16)",
      }}
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 18, alignItems: "center" }}>
        <div>
          <div
            aria-hidden="true"
            style={{
              width: 42,
              height: 42,
              borderRadius: 10,
              background: "rgba(15,122,87,0.22)",
              color: "#8fd6b2",
              display: "grid",
              placeItems: "center",
              marginBottom: 14,
            }}
          >
            <Icon d={I.target} size={20} />
          </div>
          <p style={{ margin: 0, color: "#8fd6b2", fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
            Recommended for you
          </p>
          <h2
            id="recommended-strategy-heading"
            style={{
              margin: "7px 0 0",
              color: "var(--paper)",
              fontFamily: "var(--serif)",
              fontSize: 32,
              fontWeight: 600,
              lineHeight: 1.1,
            }}
          >
            {starter.name}
          </h2>
          <p
            style={{
              margin: "8px 0 0",
              maxWidth: 720,
              color: "#d8cfb8",
              fontSize: 14,
              lineHeight: 1.55,
              fontStyle: "italic",
            }}
          >
            Where should I look first for a rank-and-rent opportunity?
          </p>
          <p style={{ margin: "8px 0 0", maxWidth: 720, color: "#eee7d7", fontSize: 14, lineHeight: 1.55 }}>
            {starter.description} Start here when you want one focused lens instead of a broad browse.
          </p>
          <div style={{ marginTop: 14, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span className="chip" style={{ cursor: "default", background: "rgba(255,255,255,0.08)", borderColor: "rgba(255,255,255,0.18)", color: "#eee7d7" }}>
              {starter.strategy_id}
            </span>
            <span className="chip" style={{ cursor: "default", background: "rgba(255,255,255,0.08)", borderColor: "rgba(255,255,255,0.18)", color: "#eee7d7" }}>
              {inputShapeLabel(starter)}
            </span>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, alignItems: "stretch" }}>
          <Link
            href={primaryHref}
            className="btn-primary"
            style={{ justifyContent: "center", textDecoration: "none", whiteSpace: "normal", background: "var(--accent)" }}
            aria-label={`Open recommended strategy ${starter.name}`}
          >
            {canRunFresh ? `Run ${starter.name}` : "Explore cached reports"} <Icon d={I.arrow} />
          </Link>
          <Link href="/strategies" style={{ color: "#eee7d7", fontSize: 12, fontWeight: 700, textDecoration: "underline", textUnderlineOffset: 3 }}>
            See all strategies
          </Link>
        </div>
      </div>
    </section>
  );
}

function SecondaryCards({ dashboard }: { dashboard: DashboardData }) {
  return (
    <section aria-label="Dashboard destinations" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 14 }}>
      <Card ariaLabelledBy="explore-card-heading">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <h2 id="explore-card-heading" style={{ margin: 0, color: "var(--ink)", fontFamily: "var(--serif)", fontSize: 20, fontWeight: 600 }}>
              Explore cached data
            </h2>
            <p style={{ margin: "7px 0 0", color: "var(--ink-2)", fontSize: 13.5, lineHeight: 1.5, fontStyle: "italic" }}>
              Browse for free. No scans consumed.
            </p>
          </div>
          <div>
            <ActionLink href="/explore" variant="ghost">
              Open Explore <Icon d={I.arrow} />
            </ActionLink>
          </div>
        </div>
      </Card>

      <Card ariaLabelledBy="multi-market-card-heading">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <h2 id="multi-market-card-heading" style={{ margin: 0, color: "var(--ink)", fontFamily: "var(--serif)", fontSize: 20, fontWeight: 600 }}>
              Multi-market scan
            </h2>
            <p style={{ margin: "7px 0 0", color: "var(--ink-2)", fontSize: 13.5, lineHeight: 1.5, fontStyle: "italic" }}>
              For agencies and scaled operators.
            </p>
          </div>
          {dashboard.multi_market_available ? (
            <div>
              <ActionLink href="/agency" variant="ghost">
                Open agency tools <Icon d={I.arrow} />
              </ActionLink>
            </div>
          ) : (
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
          )}
        </div>
      </Card>
    </section>
  );
}

function StrategyShortcuts({ dashboard }: { dashboard: DashboardData }) {
  return (
    <Card ariaLabelledBy="strategy-shortcuts-heading">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12, marginBottom: 12 }}>
        <h2 id="strategy-shortcuts-heading" style={{ margin: 0, color: "var(--ink)", fontFamily: "var(--serif)", fontSize: 20, fontWeight: 600 }}>
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
        <h2 id="recent-reports-heading" style={{ margin: 0, color: "var(--ink)", fontFamily: "var(--serif)", fontSize: 20, fontWeight: 600 }}>
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
          <FirstRunBanner dashboard={dashboard} />
          <UsageStrip dashboard={dashboard} />
          <RecommendedHero dashboard={dashboard} />
          <SecondaryCards dashboard={dashboard} />
          <StrategyShortcuts dashboard={dashboard} />
          <RecentReports dashboard={dashboard} />
        </>
      )}
    </main>
  );
}
