import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";

export const metadata = {
  title: "Recommendations — Widby",
};

export default function RecommendationsPage() {
  return (
    <div className="app density-roomy">
      <Sidebar active="recs" />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar crumbs={["Recommendations"]} />
        <main
          style={{
            padding: "24px 32px",
            maxWidth: 1280,
            margin: "0 auto",
            width: "100%",
            display: "flex",
            flexDirection: "column",
            gap: 20,
          }}
        >
          <header>
            <h1
              style={{
                fontFamily: "var(--serif)",
                fontSize: 28,
                fontWeight: 600,
                color: "var(--ink)",
                margin: 0,
              }}
            >
              Recommendations
            </h1>
            <p
              style={{
                fontFamily: "var(--sans)",
                fontSize: 14,
                color: "var(--ink-2)",
                margin: "4px 0 0",
              }}
            >
              Synthesized opportunity recommendations from the research agent.
            </p>
          </header>

          <div
            style={{
              background: "var(--card)",
              border: "1px solid var(--rule)",
              borderRadius: 12,
              padding: "40px 32px",
              textAlign: "center",
              maxWidth: 540,
            }}
          >
            <div
              style={{
                fontFamily: "var(--serif)",
                fontSize: 16,
                fontWeight: 600,
                color: "var(--ink)",
                marginBottom: 8,
              }}
            >
              Coming soon
            </div>
            <p
              style={{
                fontFamily: "var(--serif)",
                fontStyle: "italic",
                fontSize: 14,
                color: "var(--ink-2)",
                margin: "0 0 18px",
                lineHeight: 1.6,
              }}
            >
              Synthesized opportunity recommendations from the research agent
              will surface here. Until then, score niches directly.
            </p>
            <Link
              href="/niche-finder"
              className="btn-primary"
              style={{ textDecoration: "none", display: "inline-flex" }}
            >
              Open niche finder
            </Link>
          </div>
        </main>
      </div>
    </div>
  );
}
