"use client";

import { useMemo, useState, type ReactNode } from "react";
import Term from "@/components/glossary/Term";
import { Icon, I } from "@/lib/icons";
import type { StrategyCatalogEntry, StrategyCatalogResponse } from "@/lib/strategies/types";
import { sortByStrategyPathOrder } from "@/lib/strategies/path-registry";
import StrategyPageClient from "./[id]/StrategyPageClient";

export interface StrategyPathUnlockState {
  has_completed_scan: boolean;
  has_ranked_site_declaration: boolean;
}

const DEFAULT_UNLOCK_STATE: StrategyPathUnlockState = {
  has_completed_scan: false,
  has_ranked_site_declaration: false,
};

const inputLabels: Record<StrategyCatalogEntry["input_shape"], string> = {
  city_service: "City + service",
  city_service_keyword: "City + service + keyword",
  reference_city_service: "Reference city + service",
  cached_scan: "Cached scan",
};

function strategyTitle(strategy: StrategyCatalogEntry): ReactNode {
  if (strategy.strategy_id === "portfolio_builder") {
    return <Term termKey="portfolio_builder" label={strategy.name} />;
  }
  return strategy.name;
}

function textWithTerm(text: string, term: { label: string; termKey: string }): ReactNode {
  const index = text.toLocaleLowerCase().indexOf(term.label.toLocaleLowerCase());
  if (index < 0) return text;
  const matchedLabel = text.slice(index, index + term.label.length);
  return (
    <>
      {text.slice(0, index)}
      <Term termKey={term.termKey} label={matchedLabel} />
      {text.slice(index + term.label.length)}
    </>
  );
}

function strategyDescription(strategy: StrategyCatalogEntry): ReactNode {
  if (strategy.strategy_id === "expand_conquer") {
    return textWithTerm(strategy.description, { termKey: "lookalike", label: "lookalike" });
  }
  return strategy.description;
}

function unlockLabel(strategy: StrategyCatalogEntry): ReactNode {
  const requirement = strategy.unlock_requirement;
  if (!requirement) return null;
  if (requirement.requirement_id === "feasibility_preflight") {
    return textWithTerm(requirement.label, { termKey: "feasibility", label: "Feasibility" });
  }
  if (requirement.requirement_id === "ranked_site_declaration") {
    return textWithTerm(requirement.label, { termKey: "ranked_site", label: "Ranked site" });
  }
  return requirement.label;
}

function isUnlocked(strategy: StrategyCatalogEntry, unlockState: StrategyPathUnlockState) {
  if (strategy.is_runnable === false || strategy.path_role === "locked_teaser") return false;
  const requirementId = strategy.unlock_requirement?.requirement_id ?? "none";
  if (requirementId === "none") return true;
  if (requirementId === "scan_completed") return unlockState.has_completed_scan;
  if (requirementId === "ranked_site_declaration") {
    return unlockState.has_ranked_site_declaration;
  }
  if (requirementId === "feasibility_preflight") return true;
  return false;
}

function currentPathStrategyId(unlockState: StrategyPathUnlockState) {
  if (unlockState.has_ranked_site_declaration) return "expand_conquer";
  if (unlockState.has_completed_scan) return "gbp_blitz";
  return "easy_win";
}

function lockMessage(strategy: StrategyCatalogEntry) {
  const requirementId = strategy.unlock_requirement?.requirement_id;
  if (strategy.path_role === "locked_teaser" || requirementId === "future_release") {
    return "Future path node; not runnable in this project.";
  }
  if (requirementId === "scan_completed") return "Complete a scan to unlock this step.";
  if (requirementId === "ranked_site_declaration") {
    return "Declare a ranked site to unlock this expansion step.";
  }
  return "This strategy is not available yet.";
}

function StrategyPathNode({
  strategy,
  unlockState,
  selected,
  current,
  onSelect,
}: {
  strategy: StrategyCatalogEntry;
  unlockState: StrategyPathUnlockState;
  selected: boolean;
  current: boolean;
  onSelect: (strategy: StrategyCatalogEntry) => void;
}) {
  const unlocked = isUnlocked(strategy, unlockState);
  const locked = !unlocked;
  const sideBranch = strategy.path_role === "side_branch";
  const lockedTeaser = strategy.path_role === "locked_teaser";
  const unlock = unlockLabel(strategy);

  return (
    <article
      style={{
        background: selected ? "var(--accent-soft)" : "var(--card)",
        border: selected ? "1px solid var(--accent)" : "1px solid var(--rule)",
        borderRadius: 8,
        padding: 14,
        display: "grid",
        gap: 12,
        minHeight: 188,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
        <div>
          <div style={{ color: "var(--ink-3)", fontFamily: "var(--mono)", fontSize: 12 }}>
            {sideBranch ? "Side branch" : lockedTeaser ? "Future" : `Step ${strategy.path_order ?? ""}`}
          </div>
          <h2 style={{ fontFamily: "var(--serif)", fontSize: 18, margin: "5px 0 0", color: "var(--ink)" }}>
            {strategyTitle(strategy)}
          </h2>
        </div>
        {current ? (
          <span
            style={{
              alignSelf: "flex-start",
              border: "1px solid var(--accent)",
              borderRadius: 999,
              color: "var(--accent-ink)",
              background: "var(--accent-soft)",
              fontSize: 11,
              fontWeight: 800,
              padding: "4px 8px",
              whiteSpace: "nowrap",
            }}
          >
            Current
          </span>
        ) : null}
      </div>

      <p style={{ color: "var(--ink-2)", fontSize: 13, lineHeight: 1.5, margin: 0 }}>
        {strategyDescription(strategy)}
      </p>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <span style={{ color: "var(--ink-3)", fontSize: 12 }}>{inputLabels[strategy.input_shape]}</span>
        {unlock ? <span style={{ color: "var(--ink-3)", fontSize: 12 }}>Unlock: {unlock}</span> : null}
      </div>

      {locked ? (
        <div
          aria-label={`${strategy.name} is locked`}
          aria-disabled="true"
          style={{
            marginTop: "auto",
            color: "var(--warn)",
            background: "var(--warn-soft)",
            border: "1px solid var(--rule)",
            borderRadius: 8,
            padding: "9px 10px",
            fontSize: 12,
            lineHeight: 1.45,
          }}
        >
          {lockMessage(strategy)}
        </div>
      ) : (
        <button
          type="button"
          className={selected ? "btn-primary" : "btn-ghost"}
          aria-pressed={selected}
          onClick={() => onSelect(strategy)}
          style={{ marginTop: "auto", justifySelf: "start" }}
        >
          {selected ? "Working here" : "Work this step"} <Icon d={I.arrow} />
        </button>
      )}
    </article>
  );
}

export default function StrategiesGalleryClient({
  catalog,
  unlockState = DEFAULT_UNLOCK_STATE,
}: {
  catalog: StrategyCatalogResponse;
  unlockState?: StrategyPathUnlockState;
}) {
  const pathSteps = useMemo(
    () => sortByStrategyPathOrder(catalog.strategies.filter((strategy) => strategy.path_role === "rail_step")),
    [catalog.strategies],
  );
  const sideBranches = useMemo(
    () => sortByStrategyPathOrder(catalog.strategies.filter((strategy) => strategy.path_role === "side_branch")),
    [catalog.strategies],
  );
  const lockedTeasers = useMemo(
    () => sortByStrategyPathOrder(catalog.strategies.filter((strategy) => strategy.path_role === "locked_teaser")),
    [catalog.strategies],
  );
  const runnableStrategies = useMemo(
    () =>
      [...pathSteps, ...sideBranches].filter((strategy) =>
        isUnlocked(strategy, unlockState),
      ),
    [pathSteps, sideBranches, unlockState],
  );
  const currentStrategyId = currentPathStrategyId(unlockState);
  const initialStrategy =
    runnableStrategies.find((strategy) => strategy.strategy_id === currentStrategyId) ??
    runnableStrategies[0] ??
    pathSteps[0] ??
    sideBranches[0];
  const [selectedStrategyId, setSelectedStrategyId] = useState(
    initialStrategy?.strategy_id ?? "easy_win",
  );
  const selectedStrategy =
    runnableStrategies.find((strategy) => strategy.strategy_id === selectedStrategyId) ??
    initialStrategy;
  const aiModifier = catalog.global_modifiers.find((modifier) => modifier.modifier_id === "ai_resilience");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <header style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h1 className="page-h1" style={{ margin: 0 }}>
            Strategy path
          </h1>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Work the launch path from first scan to expansion, with risky keyword moves gated before spend.
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

      <section aria-label="B2 strategy path rail">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))",
            gap: 12,
          }}
        >
          {pathSteps.map((strategy) => (
            <StrategyPathNode
              key={strategy.strategy_id}
              strategy={strategy}
              unlockState={unlockState}
              selected={selectedStrategy?.strategy_id === strategy.strategy_id}
              current={currentStrategyId === strategy.strategy_id}
              onSelect={(nextStrategy) => setSelectedStrategyId(nextStrategy.strategy_id)}
            />
          ))}
        </div>
      </section>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))",
          gap: 18,
          alignItems: "start",
        }}
      >
        <section aria-label="Inline strategy workbench">
          {selectedStrategy ? (
            <StrategyPageClient key={selectedStrategy.strategy_id} strategy={selectedStrategy} />
          ) : (
            <div
              style={{
                background: "var(--card)",
                border: "1px solid var(--rule)",
                borderRadius: 8,
                padding: 18,
                color: "var(--ink-2)",
              }}
            >
              No runnable strategy is available.
            </div>
          )}
        </section>

        <aside style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {sideBranches.length > 0 ? (
            <section aria-label="Keyword Hijack side branch">
              <h2 style={{ fontSize: 13, color: "var(--ink-3)", textTransform: "uppercase", fontWeight: 800, margin: "0 0 10px" }}>
                Side branch
              </h2>
              <div style={{ display: "grid", gap: 12 }}>
                {sideBranches.map((strategy) => (
                  <StrategyPathNode
                    key={strategy.strategy_id}
                    strategy={strategy}
                    unlockState={unlockState}
                    selected={selectedStrategy?.strategy_id === strategy.strategy_id}
                    current={false}
                    onSelect={(nextStrategy) => setSelectedStrategyId(nextStrategy.strategy_id)}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {lockedTeasers.length > 0 ? (
            <section aria-label="Future path node">
              <h2 style={{ fontSize: 13, color: "var(--ink-3)", textTransform: "uppercase", fontWeight: 800, margin: "0 0 10px" }}>
                Future
              </h2>
              <div style={{ display: "grid", gap: 12 }}>
                {lockedTeasers.map((strategy) => (
                  <StrategyPathNode
                    key={strategy.strategy_id}
                    strategy={strategy}
                    unlockState={unlockState}
                    selected={false}
                    current={false}
                    onSelect={(nextStrategy) => setSelectedStrategyId(nextStrategy.strategy_id)}
                  />
                ))}
              </div>
            </section>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
