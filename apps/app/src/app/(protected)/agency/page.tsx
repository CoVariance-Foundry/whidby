import Link from "next/link";
import { Icon, I } from "@/lib/icons";

const lanes = [
  {
    href: "/explore",
    label: "Explore markets",
    eyebrow: "City catalog",
    copy: "Compare metros, services, density, and cached score freshness.",
  },
  {
    href: "/strategies",
    label: "Strategy lenses",
    eyebrow: "Ranking views",
    copy: "Review expansion, conquer, and exposure angles across market sets.",
  },
  {
    href: "/reports",
    label: "Saved reports",
    eyebrow: "Research history",
    copy: "Return to generated niche scores and prior market research runs.",
  },
] as const;

export default function AgencyPage() {
  return (
    <main
      className="page"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        maxWidth: 1280,
        margin: "0 auto",
        width: "100%",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: 18,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1
            style={{
              fontFamily: "var(--serif)",
              fontSize: 28,
              fontWeight: 600,
              color: "var(--ink)",
              margin: 0,
            }}
          >
            Multi-market
          </h1>
          <p
            style={{
              fontFamily: "var(--sans)",
              fontSize: 14,
              color: "var(--ink-2)",
              margin: "4px 0 0",
            }}
          >
            Coordinate city and service comparisons across active research.
          </p>
        </div>
        <Link href="/explore" className="btn-primary" style={{ textDecoration: "none" }}>
          <Icon d={I.search} /> Browse markets
        </Link>
      </header>

      <section
        aria-label="Multi-market workspaces"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 14,
        }}
      >
        {lanes.map((lane) => (
          <Link
            key={lane.href}
            href={lane.href}
            style={{
              textDecoration: "none",
              color: "inherit",
              display: "flex",
              flexDirection: "column",
              gap: 10,
              minHeight: 156,
              border: "1px solid var(--rule)",
              borderRadius: 8,
              background: "var(--card)",
              padding: 18,
            }}
          >
            <span
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: "var(--accent-ink)",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
              }}
            >
              {lane.eyebrow}
            </span>
            <strong
              style={{
                fontFamily: "var(--serif)",
                fontSize: 22,
                color: "var(--ink)",
              }}
            >
              {lane.label}
            </strong>
            <span
              style={{
                fontSize: 14,
                lineHeight: 1.5,
                color: "var(--ink-2)",
              }}
            >
              {lane.copy}
            </span>
          </Link>
        ))}
      </section>
    </main>
  );
}
