import Link from "next/link";
import { Icon, I } from "@/lib/icons";
import StatCardRow from "@/components/home/StatCardRow";
import HeroQuickSearch from "@/components/home/HeroQuickSearch";
import RecommendedMetros from "@/components/home/RecommendedMetros";
import RecentActivityFeed from "@/components/home/RecentActivityFeed";
import SavedSearchesBlock from "@/components/home/SavedSearchesBlock";
import { loadDashboard } from "@/lib/home/load-dashboard";

export default async function HomePage() {
  const dashboard = await loadDashboard();

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
            Good work today.
          </h1>
          <p
            style={{
              fontFamily: "var(--sans)",
              fontSize: 14,
              color: "var(--ink-2)",
              margin: "4px 0 0",
            }}
          >
            Your niche-scoring snapshot.
          </p>
        </div>
        <Link href="/niche-finder" className="btn-primary" style={{ textDecoration: "none" }}>
          <Icon d={I.plus} /> New report
        </Link>
      </header>

      <StatCardRow stats={dashboard.stat_cards} />

      <HeroQuickSearch />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gap: 16,
        }}
      >
        <RecommendedMetros items={dashboard.recommended} />
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <RecentActivityFeed items={dashboard.recent} />
          <SavedSearchesBlock />
        </div>
      </div>
    </main>
  );
}
