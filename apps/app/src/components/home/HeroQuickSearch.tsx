import Link from "next/link";

export default function HeroQuickSearch() {
  return (
    <section
      aria-label="Quick search"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: "22px 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div
          style={{
            fontFamily: "var(--serif)",
            fontSize: 20,
            fontWeight: 600,
            color: "var(--ink)",
          }}
        >
          Start a niche scoring run
        </div>
        <div
          style={{
            fontFamily: "var(--sans)",
            fontSize: 13.5,
            color: "var(--ink-2)",
          }}
        >
          Enter a city and service to generate an opportunity score.
        </div>
      </div>
      <Link
        href="/niche-finder"
        style={{
          fontFamily: "var(--sans)",
          fontSize: 13.5,
          fontWeight: 600,
          color: "var(--card)",
          background: "var(--accent)",
          padding: "10px 18px",
          borderRadius: 8,
          textDecoration: "none",
          whiteSpace: "nowrap",
        }}
      >
        Open niche finder
      </Link>
    </section>
  );
}
