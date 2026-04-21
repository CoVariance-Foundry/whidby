export interface ActivityItem {
  id: string;
  niche: string;
  city: string;
  created_at: string;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function RecentActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <section
      aria-labelledby="recent-heading"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: "18px 20px",
      }}
    >
      <h2
        id="recent-heading"
        style={{
          fontFamily: "var(--serif)",
          fontSize: 18,
          fontWeight: 600,
          color: "var(--ink)",
          margin: "0 0 12px",
        }}
      >
        Recent activity
      </h2>
      {items.length === 0 ? (
        <p
          style={{
            fontFamily: "var(--sans)",
            fontSize: 13.5,
            color: "var(--ink-2)",
          }}
        >
          No recent activity. Score a niche to see it here.
        </p>
      ) : (
        <ul
          style={{
            listStyle: "none",
            margin: 0,
            padding: 0,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          {items.map((item) => (
            <li
              key={item.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                padding: "8px 0",
                borderBottom: "1px solid var(--rule)",
                fontFamily: "var(--sans)",
                fontSize: 13.5,
              }}
            >
              <span style={{ color: "var(--ink)" }}>
                {item.niche} · {item.city}
              </span>
              <span
                style={{
                  color: "var(--ink-3)",
                  fontFamily: "var(--mono)",
                  fontSize: 12,
                }}
              >
                {formatDate(item.created_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
