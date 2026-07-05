import {
  proxyStrategyJsonResponse,
  proxyStrategyResponse,
} from "@/lib/strategies/api";
import { strategyAccentForId } from "@/lib/design-tokens";
import type { StrategyCatalogEntry, StrategyCatalogResponse } from "@/lib/strategies/types";
import {
  getStrategyPathNode,
  getVisibleStrategyPathNodes,
  isUserFacingStrategyId,
  sortByStrategyPathOrder,
} from "@/lib/strategies/path-registry";

function withStrategyMetadata(strategy: StrategyCatalogEntry): StrategyCatalogEntry {
  const pathNode = getStrategyPathNode(strategy.strategy_id);
  const accent_id = strategy.accent_id ?? strategy.strategy_id;
  const accent = strategyAccentForId(accent_id);

  // The synthesis reflow registry is the client availability contract; upstream
  // catalog responses can enrich known strategies, but not unlock deferred nodes.
  return {
    ...strategy,
    ...(pathNode
      ? {
          status: pathNode.status,
          input_shape: pathNode.input_shape,
          path_role: pathNode.path_role,
          path_order: pathNode.path_order,
          is_visible: pathNode.is_visible,
          is_runnable: pathNode.is_runnable,
          unlock_requirement: pathNode.unlock_requirement,
        }
      : {}),
    accent_id: accent.accent_id,
    accent,
  };
}

export const FALLBACK_STRATEGY_CATALOG: StrategyCatalogResponse = {
  strategies: getVisibleStrategyPathNodes().map((node) =>
    withStrategyMetadata({
      strategy_id: node.strategy_id,
      name: node.name,
      description: node.description,
      status: node.status,
      input_shape: node.input_shape,
    }),
  ),
  global_modifiers: [
    {
      modifier_id: "ai_resilience",
      name: "AI Resilience",
      behavior: "warn_not_hide",
    },
  ],
};

function isStrategyCatalogResponse(value: unknown): value is StrategyCatalogResponse {
  if (!value || typeof value !== "object") return false;
  return Array.isArray((value as { strategies?: unknown }).strategies);
}

export function filterStrategyCatalog(catalog: StrategyCatalogResponse): StrategyCatalogResponse {
  const fallbackById = new Map(
    FALLBACK_STRATEGY_CATALOG.strategies.map((strategy) => [strategy.strategy_id, strategy]),
  );
  const upstreamStrategies = catalog.strategies
    .filter((strategy) => isUserFacingStrategyId(strategy.strategy_id))
    .map((strategy) => ({
      ...fallbackById.get(strategy.strategy_id),
      ...strategy,
    }))
    .map(withStrategyMetadata);

  if (upstreamStrategies.length === 0) return FALLBACK_STRATEGY_CATALOG;

  const upstreamIds = new Set(upstreamStrategies.map((strategy) => strategy.strategy_id));
  const lockedTeasers = FALLBACK_STRATEGY_CATALOG.strategies.filter(
    (strategy) => strategy.path_role === "locked_teaser" && !upstreamIds.has(strategy.strategy_id),
  );
  const strategies: StrategyCatalogEntry[] = sortByStrategyPathOrder([
    ...upstreamStrategies,
    ...lockedTeasers,
  ]);

  return {
    strategies,
    global_modifiers: catalog.global_modifiers?.length
      ? catalog.global_modifiers
      : FALLBACK_STRATEGY_CATALOG.global_modifiers,
  };
}

export async function loadStrategyCatalog(): Promise<StrategyCatalogResponse> {
  try {
    const upstream = await proxyStrategyResponse("/api/strategies", { method: "GET" });
    if (!upstream.ok) return FALLBACK_STRATEGY_CATALOG;
    const response = await proxyStrategyJsonResponse(upstream);
    const body = (await response.json()) as unknown;
    if (!isStrategyCatalogResponse(body)) return FALLBACK_STRATEGY_CATALOG;
    return filterStrategyCatalog(body);
  } catch {
    return FALLBACK_STRATEGY_CATALOG;
  }
}

export async function loadStrategy(strategyId: string): Promise<StrategyCatalogEntry | undefined> {
  const catalog = await loadStrategyCatalog();
  return catalog.strategies.find(
    (strategy) => strategy.strategy_id === strategyId && strategy.is_runnable !== false,
  );
}
