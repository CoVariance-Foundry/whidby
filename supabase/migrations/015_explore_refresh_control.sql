-- 015_explore_refresh_control.sql
-- Explore refresh policy, run lineage, and report snapshot history.

CREATE TABLE IF NOT EXISTS public.explore_refresh_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL DEFAULT 'base-30-day-refresh',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    cadence_days INTEGER NOT NULL DEFAULT 30 CHECK (cadence_days BETWEEN 1 AND 365),
    scope TEXT NOT NULL DEFAULT 'all_cached'
        CHECK (scope IN ('all_cached', 'stale_only', 'filtered')),
    flags JSONB NOT NULL DEFAULT '{
        "force": false,
        "dry_run": false,
        "strategy_profile": "balanced",
        "max_items": 50,
        "concurrency": 2
    }'::jsonb,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.explore_refresh_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL REFERENCES public.explore_refresh_policies(id) ON DELETE CASCADE,
    niche_keyword TEXT NOT NULL CHECK (length(trim(niche_keyword)) > 0),
    niche_normalized TEXT NOT NULL CHECK (length(trim(niche_normalized)) > 0),
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code),
    cbsa_name TEXT NOT NULL CHECK (length(trim(cbsa_name)) > 0),
    state TEXT,
    latest_report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    latest_scored_at TIMESTAMPTZ,
    next_refresh_at TIMESTAMPTZ,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (policy_id, niche_normalized, cbsa_code)
);

CREATE TABLE IF NOT EXISTS public.explore_refresh_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES public.explore_refresh_policies(id) ON DELETE SET NULL,
    mode TEXT NOT NULL CHECK (mode IN ('manual', 'scheduled')),
    scope TEXT NOT NULL CHECK (scope IN ('selected', 'visible', 'stale', 'all')),
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'partial_failed', 'failed', 'canceled')),
    flags JSONB NOT NULL DEFAULT '{}'::jsonb,
    requested_by UUID,
    target_count INTEGER NOT NULL DEFAULT 0 CHECK (target_count >= 0),
    success_count INTEGER NOT NULL DEFAULT 0 CHECK (success_count >= 0),
    failure_count INTEGER NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.explore_refresh_run_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES public.explore_refresh_runs(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES public.explore_refresh_targets(id) ON DELETE CASCADE,
    old_report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    new_report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'skipped')),
    error_message TEXT,
    opportunity_before INTEGER CHECK (opportunity_before BETWEEN 0 AND 100),
    opportunity_after INTEGER CHECK (opportunity_after BETWEEN 0 AND 100),
    score_delta INTEGER,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.explore_report_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES public.reports(id) ON DELETE CASCADE,
    run_id UUID REFERENCES public.explore_refresh_runs(id) ON DELETE SET NULL,
    target_id UUID REFERENCES public.explore_refresh_targets(id) ON DELETE SET NULL,
    niche_keyword TEXT NOT NULL CHECK (length(trim(niche_keyword)) > 0),
    niche_normalized TEXT NOT NULL CHECK (length(trim(niche_normalized)) > 0),
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code),
    cbsa_name TEXT NOT NULL CHECK (length(trim(cbsa_name)) > 0),
    state TEXT,
    strategy_profile TEXT NOT NULL DEFAULT 'balanced',
    scored_at TIMESTAMPTZ NOT NULL,
    opportunity_score INTEGER CHECK (opportunity_score BETWEEN 0 AND 100),
    demand_score INTEGER CHECK (demand_score BETWEEN 0 AND 100),
    organic_competition_score INTEGER CHECK (organic_competition_score BETWEEN 0 AND 100),
    local_competition_score INTEGER CHECK (local_competition_score BETWEEN 0 AND 100),
    monetization_score INTEGER CHECK (monetization_score BETWEEN 0 AND 100),
    ai_resilience_score INTEGER CHECK (ai_resilience_score BETWEEN 0 AND 100),
    confidence_score INTEGER CHECK (confidence_score BETWEEN 0 AND 100),
    serp_archetype TEXT,
    ai_exposure TEXT,
    difficulty_tier TEXT,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (report_id, cbsa_code)
);

CREATE INDEX IF NOT EXISTS idx_explore_targets_due
    ON public.explore_refresh_targets(next_refresh_at, priority)
    WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_explore_targets_market
    ON public.explore_refresh_targets(niche_normalized, cbsa_code);
CREATE INDEX IF NOT EXISTS idx_explore_runs_status
    ON public.explore_refresh_runs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_explore_run_items_run
    ON public.explore_refresh_run_items(run_id, status);
CREATE INDEX IF NOT EXISTS idx_explore_snapshots_target_time
    ON public.explore_report_snapshots(target_id, scored_at DESC);
CREATE INDEX IF NOT EXISTS idx_explore_snapshots_market_time
    ON public.explore_report_snapshots(niche_normalized, cbsa_code, scored_at DESC);

CREATE OR REPLACE VIEW public.explore_latest_target_scores AS
SELECT DISTINCT ON (target_id)
    target_id,
    report_id,
    niche_keyword,
    niche_normalized,
    cbsa_code,
    cbsa_name,
    state,
    strategy_profile,
    scored_at,
    opportunity_score,
    demand_score,
    organic_competition_score,
    local_competition_score,
    monetization_score,
    ai_resilience_score,
    confidence_score,
    serp_archetype,
    ai_exposure,
    difficulty_tier,
    meta
FROM public.explore_report_snapshots
WHERE target_id IS NOT NULL
ORDER BY target_id, scored_at DESC;

CREATE OR REPLACE VIEW public.explore_target_trends AS
SELECT
    s.*,
    LAG(opportunity_score) OVER (
        PARTITION BY target_id
        ORDER BY scored_at
    ) AS previous_opportunity_score,
    opportunity_score - LAG(opportunity_score) OVER (
        PARTITION BY target_id
        ORDER BY scored_at
    ) AS opportunity_delta
FROM public.explore_report_snapshots s
WHERE target_id IS NOT NULL;

ALTER TABLE public.explore_refresh_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.explore_refresh_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.explore_refresh_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.explore_refresh_run_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.explore_report_snapshots ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can read explore refresh policies"
    ON public.explore_refresh_policies;
CREATE POLICY "Authenticated users can read explore refresh policies"
    ON public.explore_refresh_policies FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Authenticated users can read explore refresh targets"
    ON public.explore_refresh_targets;
CREATE POLICY "Authenticated users can read explore refresh targets"
    ON public.explore_refresh_targets FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Authenticated users can read explore refresh runs"
    ON public.explore_refresh_runs;
CREATE POLICY "Authenticated users can read explore refresh runs"
    ON public.explore_refresh_runs FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Authenticated users can read explore refresh run items"
    ON public.explore_refresh_run_items;
CREATE POLICY "Authenticated users can read explore refresh run items"
    ON public.explore_refresh_run_items FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Authenticated users can read explore report snapshots"
    ON public.explore_report_snapshots;
CREATE POLICY "Authenticated users can read explore report snapshots"
    ON public.explore_report_snapshots FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Service role manages explore refresh policies"
    ON public.explore_refresh_policies;
CREATE POLICY "Service role manages explore refresh policies"
    ON public.explore_refresh_policies FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role manages explore refresh targets"
    ON public.explore_refresh_targets;
CREATE POLICY "Service role manages explore refresh targets"
    ON public.explore_refresh_targets FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role manages explore refresh runs"
    ON public.explore_refresh_runs;
CREATE POLICY "Service role manages explore refresh runs"
    ON public.explore_refresh_runs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role manages explore refresh run items"
    ON public.explore_refresh_run_items;
CREATE POLICY "Service role manages explore refresh run items"
    ON public.explore_refresh_run_items FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role manages explore report snapshots"
    ON public.explore_report_snapshots;
CREATE POLICY "Service role manages explore report snapshots"
    ON public.explore_report_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true);

GRANT SELECT ON public.explore_refresh_policies TO authenticated;
GRANT SELECT ON public.explore_refresh_targets TO authenticated;
GRANT SELECT ON public.explore_refresh_runs TO authenticated;
GRANT SELECT ON public.explore_refresh_run_items TO authenticated;
GRANT SELECT ON public.explore_report_snapshots TO authenticated;
GRANT SELECT ON public.explore_latest_target_scores TO authenticated;
GRANT SELECT ON public.explore_target_trends TO authenticated;

GRANT ALL ON TABLE public.explore_refresh_policies TO service_role;
GRANT ALL ON TABLE public.explore_refresh_targets TO service_role;
GRANT ALL ON TABLE public.explore_refresh_runs TO service_role;
GRANT ALL ON TABLE public.explore_refresh_run_items TO service_role;
GRANT ALL ON TABLE public.explore_report_snapshots TO service_role;
GRANT SELECT ON public.explore_latest_target_scores TO service_role;
GRANT SELECT ON public.explore_target_trends TO service_role;
