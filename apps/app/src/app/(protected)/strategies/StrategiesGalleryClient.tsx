"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Icon, I } from "@/lib/icons";
import type { StrategyCatalogEntry, StrategyCatalogResponse } from "@/lib/strategies/types";

const inputLabels: Record<StrategyCatalogEntry["input_shape"], string> = {
  city_service: "City + service",
  city_service_keyword: "City + service + keyword",
  reference_city_service: "Reference city + service",
  cached_scan: "Cached scan",
};

const launchOrder = ["easy_win", "gbp_blitz", "keyword_hijack", "expand_conquer"];

type StrategyPresentation = {
  icon: string;
  question: string;
  aiResilient: boolean;
};

const strategyPresentation: Record<string, StrategyPresentation> = {
  easy_win: {
    icon: I.target,
    question: "Where can I rank fastest with weak competition?",
    aiResilient: true,
  },
  gbp_blitz: {
    icon: I.mapPin,
    question: "Which markets can I win through local profile gaps?",
    aiResilient: true,
  },
  keyword_hijack: {
    icon: I.search,
    question: "Which keyword opens a focused wedge?",
    aiResilient: false,
  },
  expand_conquer: {
    icon: I.map,
    question: "Where should a proven playbook expand next?",
    aiResilient: false,
  },
  cash_cow: {
    icon: I.star,
    question: "Which cached market has durable economics?",
    aiResilient: false,
  },
};

function getPresentation(strategy: StrategyCatalogEntry): StrategyPresentation {
  return (
    strategyPresentation[strategy.strategy_id] ?? {
      icon: I.sliders,
      question: "Which ranking lens should shape this market scan?",
      aiResilient: false,
    }
  );
}

function sortStrategies(a: StrategyCatalogEntry, b: StrategyCatalogEntry) {
  const ai = launchOrder.indexOf(a.strategy_id);
  const bi = launchOrder.indexOf(b.strategy_id);
  if (ai === -1 && bi === -1) return a.name.localeCompare(b.name);
  if (ai === -1) return 1;
  if (bi === -1) return -1;
  return ai - bi;
}

function StrategyCard({
  strategy,
  isRecommended,
}: {
  strategy: StrategyCatalogEntry;
  isRecommended: boolean;
}) {
  const isLocked = strategy.status === "phase_2";
  const presentation = getPresentation(strategy);
  const card = (
    <article
      className={isLocked ? undefined : "transition hover:-translate-y-0.5 hover:shadow-lg"}
      style={{
        background: "#fff",
        border: "1px solid #e5e7eb",
        borderRadius: 12,
        padding: 20,
        display: "flex",
        flexDirection: "column",
        gap: 16,
        minHeight: 260,
        color: "var(--ink)",
        opacity: isLocked ? 0.78 : 1,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <span
          aria-hidden="true"
          style={{
            width: 42,
            height: 42,
            borderRadius: 12,
            display: "grid",
            placeItems: "center",
            background: "var(--accent-soft)",
            color: "var(--accent-ink)",
            flex: "0 0 auto",
          }}
        >
          <Icon d={presentation.icon} size={20} />
        </span>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
          {isRecommended ? (
            <span
              style={{
                borderRadius: 999,
                color: "var(--accent-ink)",
                background: "var(--accent-soft)",
                fontSize: 11,
                fontWeight: 750,
                padding: "5px 9px",
                whiteSpace: "nowrap",
              }}
            >
              Recommended
            </span>
          ) : null}
          <span
            style={{
              alignSelf: "flex-start",
              border: "1px solid var(--rule-strong)",
              borderRadius: 999,
              color: isLocked ? "var(--warn)" : "var(--accent-ink)",
              background: isLocked ? "var(--warn-soft)" : "var(--accent-soft)",
              fontSize: 11,
              fontWeight: 750,
              padding: "5px 9px",
              whiteSpace: "nowrap",
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
            }}
          >
            <Icon d={isLocked ? I.lock : I.check} size={12} />
            {isLocked ? "Locked" : "Unlocked"}
          </span>
        </div>
      </div>

      <div>
        <h2 style={{ fontFamily: "var(--serif)", fontSize: 22, lineHeight: 1.15, margin: 0, color: "var(--ink)" }}>
            {strategy.name}
        </h2>
        <p
          style={{
            color: "var(--ink-3)",
            fontSize: 13,
            lineHeight: 1.45,
            fontStyle: "italic",
            margin: "8px 0 0",
          }}
        >
          {presentation.question}
        </p>
      </div>

      <p style={{ color: "var(--ink-2)", fontSize: 14, lineHeight: 1.55, margin: 0 }}>
        {strategy.description}
      </p>

      <div style={{ marginTop: "auto", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <span style={{ color: "var(--ink-3)", fontSize: 12 }}>
          {inputLabels[strategy.input_shape]}
        </span>
        <span
          style={{
            color: isLocked ? "var(--warn)" : "var(--accent-ink)",
            fontSize: 12,
            fontWeight: 750,
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          {isLocked ? "Phase 2" : "Open lens"}
          {!isLocked ? <Icon d={I.arrow} /> : null}
        </span>
      </div>
    </article>
  );

  if (isLocked) {
    return card;
  }

  return (
    <Link
      href={`/strategies/${strategy.strategy_id}`}
      style={{ textDecoration: "none", display: "block", height: "100%" }}
      aria-label={`Open ${strategy.name}`}
    >
      {card}
    </Link>
  );
}

export default function StrategiesGalleryClient({
  catalog,
  recommendedStrategyId,
  recommendationReason,
}: {
  catalog: StrategyCatalogResponse;
  recommendedStrategyId?: string;
  recommendationReason?: string;
}) {
  const [aiProofOnly, setAiProofOnly] = useState(false);
  const recommendedStrategy = catalog.strategies.find(
    (strategy) => strategy.strategy_id === recommendedStrategyId,
  );
  const visibleStrategies = useMemo(() => {
    if (!aiProofOnly) return catalog.strategies;
    return catalog.strategies.filter((strategy) => getPresentation(strategy).aiResilient);
  }, [aiProofOnly, catalog.strategies]);
  const launch = visibleStrategies.filter((strategy) => strategy.status === "launch").sort(sortStrategies);
  const phase2 = visibleStrategies
    .filter((strategy) => strategy.status === "phase_2")
    .sort((a, b) => a.name.localeCompare(b.name));
  const hasVisibleStrategies = launch.length > 0 || phase2.length > 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 18, flexWrap: "wrap" }}>
        <div style={{ maxWidth: 720 }}>
          <div
            style={{
              color: "var(--ink-3)",
              fontSize: 11,
              fontWeight: 750,
              letterSpacing: 0.8,
              textTransform: "uppercase",
              marginBottom: 8,
            }}
          >
            Strategies
          </div>
          <h1
            className="page-h1"
            style={{ margin: 0, fontFamily: "var(--serif)", fontSize: 48, lineHeight: 1.02 }}
          >
            Pick a{" "}
            <span style={{ color: "var(--accent)", fontFamily: "var(--serif)", fontStyle: "italic" }}>
              lens
            </span>
            .
          </h1>
          <p className="page-sub" style={{ maxWidth: 680, marginBottom: 0 }}>
            Use a ranking lens over cached market intelligence. Each strategy keeps the same underlying data, but changes what gets surfaced first.
          </p>
          <p style={{ color: "var(--ink-3)", fontSize: 14, lineHeight: 1.5, margin: "10px 0 0" }}>
            Not sure which lens fits?{" "}
            <Link href="/explore" style={{ color: "var(--accent-ink)", fontWeight: 700, textDecoration: "underline" }}>
              Browse Explore first
            </Link>
            .
          </p>
        </div>
        <button
          type="button"
          aria-pressed={aiProofOnly}
          onClick={() => setAiProofOnly((value) => !value)}
          style={{
            border: aiProofOnly ? "1px solid #6ee7b7" : "1px solid #e5e7eb",
            borderRadius: 999,
            background: aiProofOnly ? "#ecfdf5" : "#fff",
            color: aiProofOnly ? "var(--accent-ink)" : "var(--ink-2)",
            padding: "9px 12px",
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            fontSize: 12,
            fontWeight: 650,
            minHeight: 38,
          }}
        >
          <Icon d={I.filter} />
          AI-Proof filter {aiProofOnly ? "on" : "off"}
        </button>
      </header>

      {recommendedStrategy ? (
        <section
          aria-label="Strategy recommendation"
          className="animate-in fade-in duration-300"
          style={{
            borderRadius: 16,
            background: "#111827",
            color: "#fff",
            padding: 20,
            display: "flex",
            gap: 14,
            alignItems: "flex-start",
          }}
        >
          <span
            aria-hidden="true"
            style={{
              width: 42,
              height: 42,
              borderRadius: 12,
              display: "grid",
              placeItems: "center",
              background: "rgba(16, 185, 129, 0.15)",
              color: "#a7f3d0",
              flex: "0 0 auto",
            }}
          >
            <Icon d={I.sparkle} size={20} />
          </span>
          <div>
            <div
              style={{
                color: "#a7f3d0",
                fontSize: 10,
                fontWeight: 800,
                letterSpacing: 0.8,
                textTransform: "uppercase",
                marginBottom: 5,
              }}
            >
              Our recommendation
            </div>
            <p style={{ margin: 0, fontSize: 15, lineHeight: 1.5, color: "#f9fafb" }}>
              Start with <strong>{recommendedStrategy.name}</strong>
              {recommendationReason ? ` because ${recommendationReason}` : " based on your onboarding route"}.
            </p>
          </div>
        </section>
      ) : null}

      {hasVisibleStrategies ? (
        <>
          <section aria-labelledby="available-strategies">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <h2 id="available-strategies" style={{ fontSize: 13, color: "var(--ink-3)", textTransform: "uppercase", fontWeight: 750, margin: 0 }}>
                Available to you
              </h2>
              <span style={{ color: "var(--ink-3)", fontSize: 12 }}>{launch.length} unlocked</span>
            </div>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {launch.map((strategy) => (
                <StrategyCard
                  key={strategy.strategy_id}
                  strategy={strategy}
                  isRecommended={strategy.strategy_id === recommendedStrategy?.strategy_id}
                />
              ))}
            </div>
          </section>

          {phase2.length > 0 ? (
            <section aria-labelledby="locked-strategies">
              <h2 id="locked-strategies" style={{ fontSize: 13, color: "var(--ink-3)", textTransform: "uppercase", fontWeight: 750, margin: "0 0 14px" }}>
                Unlock as you progress
              </h2>
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {phase2.map((strategy) => (
                  <StrategyCard
                    key={strategy.strategy_id}
                    strategy={strategy}
                    isRecommended={strategy.strategy_id === recommendedStrategy?.strategy_id}
                  />
                ))}
              </div>
            </section>
          ) : null}
        </>
      ) : (
        <div
          role="status"
          style={{
            border: "1px dashed var(--rule-strong)",
            borderRadius: 12,
            background: "#fff",
            color: "var(--ink-2)",
            padding: 24,
            textAlign: "center",
          }}
        >
          No AI-proof strategies match this catalog yet.
        </div>
      )}
    </div>
  );
}
