import type { StrategyAccent, StrategyAccentId } from "@/lib/design-tokens";
import type {
  StrategyPathRole,
  StrategyUnlockMetadata,
} from "@/lib/strategies/path-registry";

export type StrategyStatus = "launch" | "phase_2" | "locked" | "deferred";

export type StrategyInputShape =
  | "city_service"
  | "city_service_keyword"
  | "reference_city_service"
  | "cached_scan";

export interface StrategyCatalogEntry {
  strategy_id: string;
  name: string;
  description: string;
  status: StrategyStatus;
  input_shape: StrategyInputShape;
  path_role?: StrategyPathRole;
  path_order?: number;
  is_visible?: boolean;
  is_runnable?: boolean;
  unlock_requirement?: StrategyUnlockMetadata;
  accent_id?: StrategyAccentId;
  accent?: StrategyAccent;
}

export interface StrategyGlobalModifier {
  modifier_id: string;
  name: string;
  behavior: string;
}

export interface StrategyCatalogResponse {
  strategies: StrategyCatalogEntry[];
  global_modifiers: StrategyGlobalModifier[];
}

export interface StrategyDiscoverRequest {
  lens_id?: string;
  primary_keyword?: string | null;
  city_filters?: Record<string, unknown>[];
  service_filters?: Record<string, unknown>[];
  portfolio_market_ids?: string[] | null;
  reference_city_id?: string | null;
  ai_resilience_filter?: boolean;
  limit?: number;
  offset?: number;
}

export interface StrategyRunRequest {
  mode?: "cached" | "fresh";
  strategy_id?: string;
  lens_id?: string;
  city?: string;
  state?: string;
  service?: string;
  primary_keyword?: string | null;
  reference_city_id?: string | null;
  feasibility_preflight_passed?: boolean;
  ai_resilience_filter?: boolean;
  limit?: number;
  targets?: Record<string, unknown>[];
  quota_consumed?: number;
}
