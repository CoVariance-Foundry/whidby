import type { MetroScores } from "@/lib/niche-finder/types";
import BreakdownPanel from "@/components/reports/BreakdownPanel";

interface Props {
  signals: Record<string, unknown>;
  scores: MetroScores;
}

export default function ScoreBreakdownTabs({ signals, scores }: Props) {
  const getSignalBlock = (key: string): Record<string, unknown> => {
    const block = signals[key];
    return block && typeof block === "object" ? (block as Record<string, unknown>) : {};
  };

  return (
    <section
      aria-label="Score breakdown"
      style={{
        borderTop: "1px solid var(--rule)",
        paddingTop: 14,
        marginTop: 4,
      }}
    >
      <div
        style={{
          display: "grid",
          gap: 10,
        }}
      >
        <div
          style={{
            padding: "4px 14px 10px",
            background: "var(--paper-alt)",
            borderRadius: 10,
            border: "1px solid var(--rule)",
          }}
        >
          <BreakdownPanel
            title="Organic ease"
            scoreKey="organic_competition"
            score={scores.organic_competition}
            category="organic_competition"
            signals={getSignalBlock("organic_competition")}
          />
          <div
            style={{
              borderTop: "1px solid var(--rule)",
              marginTop: 4,
            }}
          />
          <BreakdownPanel
            title="Local ease"
            scoreKey="local_competition"
            score={scores.local_competition}
            category="local_competition"
            signals={getSignalBlock("local_competition")}
          />
        </div>

        {[
          {
            title: "Demand",
            scoreKey: "demand" as const,
            score: scores.demand,
            category: "demand" as const,
            signals: getSignalBlock("demand"),
          },
          {
            title: "Monetization",
            scoreKey: "monetization" as const,
            score: scores.monetization,
            category: "monetization" as const,
            signals: getSignalBlock("monetization"),
          },
          {
            title: "AI Resilience",
            scoreKey: "ai_resilience" as const,
            score: scores.ai_resilience,
            category: "ai_resilience" as const,
            signals: getSignalBlock("ai_resilience"),
          },
        ].map((panel) => (
          <div
            key={panel.scoreKey}
            style={{
              padding: "4px 14px 10px",
              background: "var(--paper-alt)",
              borderRadius: 10,
              border: "1px solid var(--rule)",
            }}
          >
            <BreakdownPanel
              title={panel.title}
              scoreKey={panel.scoreKey}
              score={panel.score}
              category={panel.category}
              signals={panel.signals}
            />
          </div>
        ))}
      </div>
    </section>
  );
}
