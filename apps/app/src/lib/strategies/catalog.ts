import {
  proxyStrategyJsonResponse,
  proxyStrategyResponse,
} from "@/lib/strategies/api";
import type { StrategyCatalogEntry, StrategyCatalogResponse } from "@/lib/strategies/types";

export const FALLBACK_STRATEGY_CATALOG: StrategyCatalogResponse = {
  strategies: [
    {
      strategy_id: "easy_win",
      name: "Easy Win",
      description: "Find city and service pairs with useful demand and weaker competition.",
      status: "launch",
      input_shape: "city_service",
    },
    {
      strategy_id: "gbp_blitz",
      name: "GBP Blitz",
      description: "Prioritize markets where local pack competitors leave profile gaps.",
      status: "launch",
      input_shape: "city_service",
    },
    {
      strategy_id: "keyword_hijack",
      name: "Keyword Hijack",
      description: "Rank markets through one primary keyword lens.",
      status: "launch",
      input_shape: "city_service_keyword",
    },
    {
      strategy_id: "expand_conquer",
      name: "Expand & Conquer",
      description: "Use a reference city to find lookalike expansion markets.",
      status: "launch",
      input_shape: "reference_city_service",
    },
    {
      strategy_id: "cash_cow",
      name: "Cash Cow",
      description: "Phase-2 scan for markets with stronger lead economics.",
      status: "phase_2",
      input_shape: "cached_scan",
    },
  ],
  global_modifiers: [
    {
      modifier_id: "ai_resilience",
      name: "AI Resilience",
      behavior: "warn_not_hide",
    },
  ],
};

const allowedStrategyIds = new Set(
  FALLBACK_STRATEGY_CATALOG.strategies.map((strategy) => strategy.strategy_id),
);

function isStrategyCatalogResponse(value: unknown): value is StrategyCatalogResponse {
  if (!value || typeof value !== "object") return false;
  return Array.isArray((value as { strategies?: unknown }).strategies);
}

export function filterStrategyCatalog(catalog: StrategyCatalogResponse): StrategyCatalogResponse {
  const fallbackById = new Map(
    FALLBACK_STRATEGY_CATALOG.strategies.map((strategy) => [strategy.strategy_id, strategy]),
  );
  const strategies: StrategyCatalogEntry[] = catalog.strategies
    .filter((strategy) => allowedStrategyIds.has(strategy.strategy_id))
    .map((strategy) => ({
      ...fallbackById.get(strategy.strategy_id),
      ...strategy,
    }))
    .sort((a, b) => {
      const ai = FALLBACK_STRATEGY_CATALOG.strategies.findIndex(
        (strategy) => strategy.strategy_id === a.strategy_id,
      );
      const bi = FALLBACK_STRATEGY_CATALOG.strategies.findIndex(
        (strategy) => strategy.strategy_id === b.strategy_id,
      );
      return ai - bi;
    });

  if (strategies.length === 0) return FALLBACK_STRATEGY_CATALOG;

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
  return catalog.strategies.find((strategy) => strategy.strategy_id === strategyId);
}
