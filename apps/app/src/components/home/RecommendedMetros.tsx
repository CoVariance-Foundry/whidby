import Link from "next/link";

export interface RecommendedItem {
  id: string;
  niche: string;
  city: string;
  score: number | null;
}

export default function RecommendedMetros({ items }: { items: RecommendedItem[] }) {
  return (
    <section
      aria-labelledby="rec-heading"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: "18px 20px",
      }}
    >
      <h2
        id="rec-heading"
        style={{
          fontFamily: "var(--serif)",
          fontSize: 18,
          fontWeight: 600,
          color: "var(--ink)",
          margin: "0 0 12px",
        }}
      >
        Recommended
      </h2>
      {items.length === 0 ? (
        <p
          style={{
            fontFamily: "var(--sans)",
            fontSize: 13.5,
            color: "var(--ink-2)",
          }}
        >
          No recommendations yet. Score a niche to get started.
        </p>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: 12,
          }}
        >
          {items.slice(0, 6).map((item) => (
            <Link
              key={item.id}
              href={`/niche-finder?city=${encodeURIComponent(item.city)}&service=${encodeURIComponent(item.niche)}`}
              style={{ textDecoration: "none", color: "inherit" }}
            >
              <article
                className="report-row-clickable"
                style={{
                  background: "var(--paper)",
                  border: "1px solid var(--rule)",
                  borderRadius: 10,
                  padding: "12px 14px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 4,
                  minWidth: 0,
                  cursor: "pointer",
                  transition: "background 0.1s",
                }}
              >
                <div
                  style={{
                    fontFamily: "var(--sans)",
                    fontSize: 13.5,
                    fontWeight: 600,
                    color: "var(--ink)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {item.city}
                </div>
                <div
                  style={{
                    fontFamily: "var(--sans)",
                    fontSize: 12.5,
                    color: "var(--ink-2)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {item.niche}
                </div>
                {item.score !== null ? (
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 18,
                      fontWeight: 600,
                      color: "var(--accent-ink)",
                      marginTop: 4,
                    }}
                  >
                    {item.score}
                  </div>
                ) : null}
              </article>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
