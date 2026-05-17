export type ExploreRefreshStrategyProfile =
  | "balanced"
  | "growth"
  | "defensive";

export type ExploreRefreshScope = "selected" | "visible" | "stale" | "all";

export type ExploreRefreshRunStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "partial_failed"
  | "failed"
  | "canceled"
  | "missing";

export interface ExploreRefreshFlags {
  force: boolean;
  dry_run: boolean;
  strategy_profile: ExploreRefreshStrategyProfile;
  max_items: number;
  concurrency: number;
}

export interface ExploreRefreshRunRequest {
  scope: ExploreRefreshScope;
  target_ids?: string[];
  report_ids?: string[];
  filters?: Record<string, unknown>;
  flags?: Partial<ExploreRefreshFlags>;
}

export interface ExploreRefreshRunResponse {
  run_id: string;
  status: ExploreRefreshRunStatus;
}
