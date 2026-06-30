"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import Term from "@/components/glossary/Term";
import { Icon, I } from "@/lib/icons";
import type { StrategyCatalogEntry, StrategyCatalogResponse } from "@/lib/strategies/types";
import { sortByStrategyPathOrder } from "@/lib/strategies/path-registry";

const inputLabels: Record<StrategyCatalogEntry["input_shape"], string> = {
  city_service: "City + service",
  city_service_keyword: "City + service + keyword",
  reference_city_service: "Reference city + service",
  cached_scan: "Cached scan",
};

function pathRoleLabel(strategy: StrategyCatalogEntry) {
  if (strategy.path_role === "side_branch") return "Side branch";
  if (strategy.path_role === "locked_teaser") return "Locked";
  return "Path step";
}

function strategyTitle(strategy: StrategyCatalogEntry): ReactNode {
  if (strategy.strategy_id === "portfolio_builder") {
    return <Term termKey="portfolio_builder" label={strategy.name} />;
  }
  return strategy.name;
}

function strategyDescription(strategy: StrategyCatalogEntry): ReactNode {
  if (strategy.strategy_id === "expand_conquer") {
    return (
      <>
        Use a reference city to find <Term termKey="lookalike" label="lookalike" /> expansion
        markets.
      </>
    );
  }
  return strategy.description;
}

function unlockLabel(strategy: StrategyCatalogEntry): ReactNode {
  const requirement = strategy.unlock_requirement;
  if (!requirement) return null;
  if (requirement.requirement_id === "feasibility_preflight") {
    return (
      <>
        <Term termKey="feasibility" label="Feasibility" /> preflight
      </>
    );
  }
  if (requirement.requirement_id === "ranked_site_declaration") {
    return (
      <>
        <Term termKey="ranked_site" label="Ranked site" /> declared
      </>
    );
  }
  return requirement.label;
}

function StrategyCard({ strategy }: { strategy: StrategyCatalogEntry }) {
  const isLocked = strategy.is_runnable === false || strategy.path_role === "locked_teaser";
  const badgeColor = isLocked ? "var(--warn)" : "var(--accent)";
  const badgeBackground = isLocked ? "var(--warn-soft)" : "var(--accent-soft)";
  const unlock = unlockLabel(strategy);
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
            {strategyTitle(strategy)}
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
            color: badgeColor,
            background: badgeBackground,
            fontSize: 11,
            fontWeight: 700,
            padding: "4px 8px",
            whiteSpace: "nowrap",
          }}
        >
          {pathRoleLabel(strategy)}
        </span>
      </div>

      <p style={{ color: "var(--ink-2)", fontSize: 14, lineHeight: 1.5, margin: 0 }}>
        {strategyDescription(strategy)}
      </p>
      {unlock ? (
        <div style={{ color: "var(--ink-3)", fontSize: 12, lineHeight: 1.45 }}>
          Unlock: {unlock}
        </div>
      ) : null}

      <div style={{ marginTop: "auto", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <span style={{ color: "var(--ink-3)", fontSize: 12 }}>
          {inputLabels[strategy.input_shape]}
        </span>
        {isLocked ? (
          <span
            className="btn-ghost"
            aria-label={`${strategy.name} is locked`}
            aria-disabled="true"
            style={{ opacity: 0.72 }}
          >
            Locked
          </span>
        ) : (
          <Link
            href={`/strategies/${strategy.strategy_id}`}
            className="btn-primary"
            style={{ textDecoration: "none" }}
            aria-label={`Open ${strategy.name}`}
          >
            Open <Icon d={I.arrow} />
          </Link>
        )}
      </div>
    </article>
  );
}

export default function StrategiesGalleryClient({ catalog }: { catalog: StrategyCatalogResponse }) {
  const pathSteps = sortByStrategyPathOrder(
    catalog.strategies.filter((strategy) => strategy.path_role === "rail_step"),
  );
  const sideBranches = sortByStrategyPathOrder(
    catalog.strategies.filter((strategy) => strategy.path_role === "side_branch"),
  );
  const lockedTeasers = sortByStrategyPathOrder(
    catalog.strategies.filter((strategy) => strategy.path_role === "locked_teaser"),
  );
  const aiModifier = catalog.global_modifiers.find((modifier) => modifier.modifier_id === "ai_resilience");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <header style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h1 className="page-h1" style={{ margin: 0 }}>
            Strategy path
          </h1>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Follow the production path from first scan to expansion, with side-branch checks surfaced only where they fit the work.
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
            <strong style={{ color: "var(--ink)" }}>
              <Term termKey="ai_resilience" label={aiModifier.name} />
            </strong>
            : warnings stay visible; results are not hidden.
          </div>
        ) : null}
      </header>

      <section aria-labelledby="path-strategies">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 id="path-strategies" style={{ fontSize: 13, color: "var(--ink-3)", textTransform: "uppercase", fontWeight: 700, margin: 0 }}>
            Path steps
          </h2>
          <span style={{ color: "var(--ink-3)", fontSize: 12 }}>{pathSteps.length} available</span>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 14,
          }}
        >
          {pathSteps.map((strategy) => (
            <StrategyCard key={strategy.strategy_id} strategy={strategy} />
          ))}
        </div>
      </section>

      {sideBranches.length > 0 ? (
        <section aria-labelledby="side-branch-strategies">
          <h2 id="side-branch-strategies" style={{ fontSize: 13, color: "var(--ink-3)", textTransform: "uppercase", fontWeight: 700, margin: "0 0 12px" }}>
            Side branch
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 360px))",
              gap: 14,
            }}
          >
            {sideBranches.map((strategy) => (
              <StrategyCard key={strategy.strategy_id} strategy={strategy} />
            ))}
          </div>
        </section>
      ) : null}

      {lockedTeasers.length > 0 ? (
        <section aria-labelledby="locked-strategies">
          <h2 id="locked-strategies" style={{ fontSize: 13, color: "var(--ink-3)", textTransform: "uppercase", fontWeight: 700, margin: "0 0 12px" }}>
            Locked node
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 360px))",
              gap: 14,
            }}
          >
            {lockedTeasers.map((strategy) => (
              <StrategyCard key={strategy.strategy_id} strategy={strategy} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
