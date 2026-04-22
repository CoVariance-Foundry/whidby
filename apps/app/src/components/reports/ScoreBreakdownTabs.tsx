"use client";

import { useCallback, useState } from "react";
import type { MetroScores } from "@/lib/niche-finder/types";
import BreakdownPanel from "@/components/reports/BreakdownPanel";

type TabId = "competition" | "demand" | "monetization" | "ai_resilience";

const TABS: { id: TabId; label: string }[] = [
  { id: "competition", label: "Competition" },
  { id: "demand", label: "Demand" },
  { id: "monetization", label: "Monetization" },
  { id: "ai_resilience", label: "AI Resilience" },
];

interface Props {
  signals: Record<string, unknown>;
  scores: MetroScores;
}

export default function ScoreBreakdownTabs({ signals, scores }: Props) {
  const [activeTab, setActiveTab] = useState<TabId | null>(null);

  const handleTabClick = useCallback((id: TabId) => {
    setActiveTab((prev) => (prev === id ? null : id));
  }, []);

  const getSignalBlock = (key: string): Record<string, unknown> => {
    const block = signals[key];
    return block && typeof block === "object" ? (block as Record<string, unknown>) : {};
  };

  return (
    <div
      style={{
        borderTop: "1px solid var(--rule)",
        paddingTop: 12,
        marginTop: 4,
      }}
    >
      {/* Tab bar */}
      <div
        role="tablist"
        aria-label="Score breakdown"
        style={{
          display: "flex",
          gap: 6,
          flexWrap: "wrap",
        }}
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              aria-controls={isActive ? `panel-${tab.id}` : undefined}
              onClick={() => handleTabClick(tab.id)}
              style={{
                display: "inline-block",
                padding: "4px 12px",
                borderRadius: 999,
                fontSize: 11,
                fontFamily: "var(--sans)",
                fontWeight: 600,
                letterSpacing: "0.02em",
                textTransform: "uppercase" as const,
                border: "1px solid",
                borderColor: isActive ? "var(--accent-ink)" : "var(--rule)",
                background: isActive ? "var(--accent-bg, var(--paper-alt))" : "transparent",
                color: isActive ? "var(--accent-ink)" : "var(--ink-3)",
                cursor: "pointer",
                transition: "all 0.15s",
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Active panel */}
      {activeTab && (
        <div
          id={`panel-${activeTab}`}
          role="tabpanel"
          style={{
            marginTop: 12,
            padding: "4px 14px 10px",
            background: "var(--paper-alt)",
            borderRadius: 10,
            border: "1px solid var(--rule)",
          }}
        >
          {activeTab === "competition" && (
            <>
              <BreakdownPanel
                title="Organic Competition"
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
                title="Local Competition"
                scoreKey="local_competition"
                score={scores.local_competition}
                category="local_competition"
                signals={getSignalBlock("local_competition")}
              />
            </>
          )}

          {activeTab === "demand" && (
            <BreakdownPanel
              title="Demand"
              scoreKey="demand"
              score={scores.demand}
              category="demand"
              signals={getSignalBlock("demand")}
            />
          )}

          {activeTab === "monetization" && (
            <BreakdownPanel
              title="Monetization"
              scoreKey="monetization"
              score={scores.monetization}
              category="monetization"
              signals={getSignalBlock("monetization")}
            />
          )}

          {activeTab === "ai_resilience" && (
            <BreakdownPanel
              title="AI Resilience"
              scoreKey="ai_resilience"
              score={scores.ai_resilience}
              category="ai_resilience"
              signals={getSignalBlock("ai_resilience")}
            />
          )}
        </div>
      )}
    </div>
  );
}
