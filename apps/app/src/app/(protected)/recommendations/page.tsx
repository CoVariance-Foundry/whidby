import Link from "next/link";

export const metadata = {
  title: "Recommendations — Widby",
};

export default function RecommendationsPage() {
  return (
    <section
      style={{
        padding: "3rem 1.5rem",
        maxWidth: "640px",
        margin: "0 auto",
        textAlign: "center",
      }}
    >
      <h1
        style={{
          fontFamily: "var(--serif)",
          fontSize: "1.75rem",
          fontWeight: 500,
          marginBottom: "0.75rem",
        }}
      >
        Recommendations
      </h1>
      <p
        style={{
          color: "var(--muted)",
          lineHeight: 1.6,
          marginBottom: "2rem",
        }}
      >
        Synthesized opportunity recommendations from the research agent will
        surface here. Until then, the admin dashboard holds the current
        validated hypotheses and experiment rollups.
      </p>
      <Link
        href="/niche-finder"
        style={{
          display: "inline-block",
          padding: "0.55rem 1.1rem",
          borderRadius: "6px",
          border: "1px solid var(--rule)",
          fontFamily: "var(--mono)",
          fontSize: "0.8rem",
          textDecoration: "none",
          color: "inherit",
        }}
      >
        Score a niche instead
      </Link>
    </section>
  );
}
