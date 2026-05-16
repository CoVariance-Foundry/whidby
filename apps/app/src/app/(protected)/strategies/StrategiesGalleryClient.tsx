"use client";

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

function sortStrategies(a: StrategyCatalogEntry, b: StrategyCatalogEntry) {
  const ai = launchOrder.indexOf(a.strategy_id);
  const bi = launchOrder.indexOf(b.strategy_id);
  if (ai === -1 && bi === -1) return a.name.localeCompare(b.name);
  if (ai === -1) return 1;
  if (bi === -1) return -1;
  return ai - bi;
}

function StrategyCard({ strategy }: { strategy: StrategyCatalogEntry }) {
  const isUnavailable = strategy.input_shape === "reference_city_service" || strategy.status === "phase_2";
  return (
    <article
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: 18,
        display: "flex",
        flexDirection: "column",
        gap: 14,
        minHeight: 210,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <h2 style={{ fontFamily: "var(--serif)", fontSize: 19, margin: 0, color: "var(--ink)" }}>
            {strategy.name}
          </h2>
          <div
            style={{
              color: "var(--ink-3)",
              fontSize: 12,
              marginTop: 6,
              fontFamily: "var(--mono)",
            }}
          >
            {strategy.strategy_id}
          </div>
        </div>
        <span
          style={{
            alignSelf: "flex-start",
            border: "1px solid var(--rule-strong)",
            borderRadius: 999,
            color: strategy.status === "launch" ? "var(--accent)" : "var(--warn)",
            background: strategy.status === "launch" ? "var(--accent-soft)" : "var(--warn-soft)",
            fontSize: 11,
            fontWeight: 700,
            padding: "4px 8px",
            whiteSpace: "nowrap",
          }}
        >
          {strategy.status === "launch" ? "Launch" : "Phase 2"}
        </span>
      </div>

      <p style={{ color: "var(--ink-2)", fontSize: 14, lineHeight: 1.5, margin: 0 }}>
        {strategy.description}
      </p>

      <div style={{ marginTop: "auto", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <span style={{ color: "var(--ink-3)", fontSize: 12 }}>
          {inputLabels[strategy.input_shape]}
        </span>
        <Link
          href={`/strategies/${strategy.strategy_id}`}
          className={isUnavailable ? "btn-ghost" : "btn-primary"}
          style={{ textDecoration: "none" }}
          aria-label={`Open ${strategy.name}`}
        >
          {isUnavailable ? "View status" : "Open"} <Icon d={I.arrow} />
        </Link>
      </div>
    </article>
  );
}

export default function StrategiesGalleryClient({ catalog }: { catalog: StrategyCatalogResponse }) {
  const launch = catalog.strategies
    .filter((strategy) => strategy.status === "launch")
    .sort(sortStrategies);
  const phase2 = catalog.strategies
    .filter((strategy) => strategy.status === "phase_2")
    .sort((a, b) => a.name.localeCompare(b.name));
  const aiModifier = catalog.global_modifiers.find((modifier) => modifier.modifier_id === "ai_resilience");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <header style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h1 className="page-h1" style={{ margin: 0 }}>
            Strategy discovery
          </h1>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Use a ranking lens over cached market intelligence. Each strategy keeps the same underlying data, but changes what gets surfaced first.
          </p>
        </div>
        {aiModifier ? (
          <div
            style={{
              border: "1px solid var(--rule)",
              borderRadius: 8,
              background: "var(--card)",
              padding: "10px 12px",
              color: "var(--ink-2)",
              fontSize: 12,
              maxWidth: 320,
            }}
          >
            <strong style={{ color: "var(--ink)" }}>{aiModifier.name}</strong>: warnings stay visible; results are not hidden.
          </div>
        ) : null}
      </header>

      <section aria-labelledby="launch-strategies">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 id="launch-strategies" style={{ fontSize: 13, color: "var(--ink-3)", textTransform: "uppercase", fontWeight: 700, margin: 0 }}>
            Launch strategies
          </h2>
          <span style={{ color: "var(--ink-3)", fontSize: 12 }}>{launch.length} available</span>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 14,
          }}
        >
          {launch.map((strategy) => (
            <StrategyCard key={strategy.strategy_id} strategy={strategy} />
          ))}
        </div>
      </section>

      {phase2.length > 0 ? (
        <section aria-labelledby="phase-2-strategies">
          <h2 id="phase-2-strategies" style={{ fontSize: 13, color: "var(--ink-3)", textTransform: "uppercase", fontWeight: 700, margin: "0 0 12px" }}>
            Phase 2
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 360px))",
              gap: 14,
            }}
          >
            {phase2.map((strategy) => (
              <StrategyCard key={strategy.strategy_id} strategy={strategy} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
