export interface StatCard {
  label: string;
  value: string;
  delta?: string;
}

export default function StatCardRow({ stats }: { stats: StatCard[] }) {
  return (
    <div
      role="list"
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${stats.length}, minmax(0, 1fr))`,
        gap: 16,
      }}
    >
      {stats.map((stat) => (
        <div
          role="listitem"
          key={stat.label}
          style={{
            background: "var(--card)",
            border: "1px solid var(--rule)",
            borderRadius: 12,
            padding: "18px 20px",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <div
            style={{
              fontFamily: "var(--sans)",
              fontSize: 11.5,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--ink-3)",
            }}
          >
            {stat.label}
          </div>
          <div
            style={{
              fontFamily: "var(--serif)",
              fontSize: 32,
              fontWeight: 600,
              color: "var(--ink)",
              lineHeight: 1.1,
            }}
          >
            {stat.value}
          </div>
          {stat.delta ? (
            <div
              style={{
                fontFamily: "var(--sans)",
                fontSize: 12,
                color: "var(--ink-2)",
              }}
            >
              {stat.delta}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
