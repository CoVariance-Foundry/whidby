import type { StrategyInputShape, StrategyStatus } from "@/lib/strategies/types";

export const STRATEGY_PATH_IDS = [
  "easy_win",
  "gbp_blitz",
  "expand_conquer",
  "keyword_hijack",
  "portfolio_builder",
  "cash_cow",
  "blue_ocean",
  "seasonal_arbitrage",
] as const;

export type StrategyPathId = (typeof STRATEGY_PATH_IDS)[number];

export type StrategyPathRole =
  | "rail_step"
  | "side_branch"
  | "locked_teaser"
  | "deferred";

export type StrategyUnlockRequirementId =
  | "none"
  | "scan_completed"
  | "ranked_site_declaration"
  | "feasibility_preflight"
  | "future_release";

export interface StrategyUnlockMetadata {
  requirement_id: StrategyUnlockRequirementId;
  label: string;
  description: string;
}

export interface StrategyPathNode {
  strategy_id: StrategyPathId;
  name: string;
  description: string;
  status: StrategyStatus;
  input_shape: StrategyInputShape;
  path_role: StrategyPathRole;
  path_order: number;
  is_visible: boolean;
  is_runnable: boolean;
  unlock_requirement: StrategyUnlockMetadata;
}

export const STRATEGY_UNLOCK_REQUIREMENTS = {
  none: {
    requirement_id: "none",
    label: "Available",
    description: "No additional product state is required.",
  },
  scan_completed: {
    requirement_id: "scan_completed",
    label: "Scan completed",
    description: "A completed scan or report advances the path to this step.",
  },
  ranked_site_declaration: {
    requirement_id: "ranked_site_declaration",
    label: "Ranked site declared",
    description: "User declares an existing ranked site before expansion guidance.",
  },
  feasibility_preflight: {
    requirement_id: "feasibility_preflight",
    label: "Feasibility preflight",
    description: "Preflight must pass before spend or fresh-report quota is consumed.",
  },
  future_release: {
    requirement_id: "future_release",
    label: "Locked",
    description: "Visible as a future path node, but not runnable in this project.",
  },
} as const satisfies Record<StrategyUnlockRequirementId, StrategyUnlockMetadata>;

export const STRATEGY_PATH_REGISTRY = [
  {
    strategy_id: "easy_win",
    name: "Easy Win",
    description: "Find city and service pairs with useful demand and weaker competition.",
    status: "launch",
    input_shape: "city_service",
    path_role: "rail_step",
    path_order: 10,
    is_visible: true,
    is_runnable: true,
    unlock_requirement: STRATEGY_UNLOCK_REQUIREMENTS.none,
  },
  {
    strategy_id: "gbp_blitz",
    name: "GBP Blitz",
    description: "Prioritize markets where local pack competitors leave profile gaps.",
    status: "launch",
    input_shape: "city_service",
    path_role: "rail_step",
    path_order: 20,
    is_visible: true,
    is_runnable: true,
    unlock_requirement: STRATEGY_UNLOCK_REQUIREMENTS.scan_completed,
  },
  {
    strategy_id: "expand_conquer",
    name: "Expand & Conquer",
    description: "Use a reference city to find lookalike expansion markets.",
    status: "launch",
    input_shape: "reference_city_service",
    path_role: "rail_step",
    path_order: 30,
    is_visible: true,
    is_runnable: true,
    unlock_requirement: STRATEGY_UNLOCK_REQUIREMENTS.ranked_site_declaration,
  },
  {
    strategy_id: "keyword_hijack",
    name: "Keyword Hijack",
    description: "Rank markets through one primary keyword lens.",
    status: "launch",
    input_shape: "city_service_keyword",
    path_role: "side_branch",
    path_order: 40,
    is_visible: true,
    is_runnable: true,
    unlock_requirement: STRATEGY_UNLOCK_REQUIREMENTS.feasibility_preflight,
  },
  {
    strategy_id: "portfolio_builder",
    name: "Portfolio Builder",
    description: "Plan adjacent portfolio moves from ranked assets and saved market context.",
    status: "locked",
    input_shape: "cached_scan",
    path_role: "locked_teaser",
    path_order: 50,
    is_visible: true,
    is_runnable: false,
    unlock_requirement: STRATEGY_UNLOCK_REQUIREMENTS.future_release,
  },
  {
    strategy_id: "cash_cow",
    name: "Cash Cow",
    description: "Deferred cross-metro economics lens.",
    status: "deferred",
    input_shape: "cached_scan",
    path_role: "deferred",
    path_order: 900,
    is_visible: false,
    is_runnable: false,
    unlock_requirement: STRATEGY_UNLOCK_REQUIREMENTS.future_release,
  },
  {
    strategy_id: "blue_ocean",
    name: "Blue Ocean",
    description: "Deferred emerging-category scan.",
    status: "deferred",
    input_shape: "cached_scan",
    path_role: "deferred",
    path_order: 910,
    is_visible: false,
    is_runnable: false,
    unlock_requirement: STRATEGY_UNLOCK_REQUIREMENTS.future_release,
  },
  {
    strategy_id: "seasonal_arbitrage",
    name: "Seasonal Arbitrage",
    description: "Deferred seasonal-market scan.",
    status: "deferred",
    input_shape: "cached_scan",
    path_role: "deferred",
    path_order: 920,
    is_visible: false,
    is_runnable: false,
    unlock_requirement: STRATEGY_UNLOCK_REQUIREMENTS.future_release,
  },
] as const satisfies readonly StrategyPathNode[];

const strategyPathIdSet = new Set<string>(STRATEGY_PATH_IDS);
const strategyPathNodeById = new Map<string, StrategyPathNode>(
  STRATEGY_PATH_REGISTRY.map((node) => [node.strategy_id, node]),
);

export function isStrategyPathId(strategyId: string): strategyId is StrategyPathId {
  return strategyPathIdSet.has(strategyId);
}

export function getStrategyPathNode(strategyId: string): StrategyPathNode | undefined {
  return strategyPathNodeById.get(strategyId);
}

export function getVisibleStrategyPathNodes(): StrategyPathNode[] {
  return STRATEGY_PATH_REGISTRY.filter((node) => node.is_visible);
}

export function getRunnableStrategyPathNodes(): StrategyPathNode[] {
  return STRATEGY_PATH_REGISTRY.filter((node) => node.is_visible && node.is_runnable);
}

export function getDeferredStrategyPathNodes(): StrategyPathNode[] {
  return STRATEGY_PATH_REGISTRY.filter((node) => node.path_role === "deferred");
}

export function isUserFacingStrategyId(strategyId: string): boolean {
  return Boolean(getStrategyPathNode(strategyId)?.is_visible);
}

export function isRunnableStrategyId(strategyId: string): boolean {
  const node = getStrategyPathNode(strategyId);
  return Boolean(node?.is_visible && node.is_runnable);
}

export function sortByStrategyPathOrder<T extends { strategy_id: string; name?: string }>(
  strategies: T[],
): T[] {
  return [...strategies].sort((a, b) => {
    const aNode = getStrategyPathNode(a.strategy_id);
    const bNode = getStrategyPathNode(b.strategy_id);
    const aOrder = aNode?.path_order ?? Number.MAX_SAFE_INTEGER;
    const bOrder = bNode?.path_order ?? Number.MAX_SAFE_INTEGER;
    if (aOrder !== bOrder) return aOrder - bOrder;
    return (a.name ?? a.strategy_id).localeCompare(b.name ?? b.strategy_id);
  });
}
