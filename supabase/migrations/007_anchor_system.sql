-- 007_anchor_system.sql
-- Anchor search system: automated longitudinal data collection.

CREATE TABLE IF NOT EXISTS anchor_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche_keyword TEXT NOT NULL,
    cbsa_code TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,

    collect_serp BOOLEAN DEFAULT true,
    collect_keyword_volume BOOLEAN DEFAULT true,
    collect_reviews BOOLEAN DEFAULT true,
    collect_gbp BOOLEAN DEFAULT false,
    collect_lighthouse BOOLEAN DEFAULT false,

    tracked_keywords JSONB NOT NULL,
    keywords_sourced_from TEXT,
    keywords_refreshed_at TIMESTAMPTZ,

    frequency TEXT NOT NULL DEFAULT 'daily'
        CHECK (frequency IN ('daily', 'weekly', 'monthly')),
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,

    max_daily_cost_usd NUMERIC(10,2) DEFAULT 1.00,
    cumulative_cost_usd NUMERIC(10,2) DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(niche_keyword, cbsa_code)
);

CREATE INDEX idx_anchor_configs_enabled ON anchor_configs (enabled, next_run_at);

CREATE TABLE IF NOT EXISTS anchor_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchor_config_id UUID NOT NULL REFERENCES anchor_configs(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'failed', 'budget_exceeded')),
    observations_created INTEGER DEFAULT 0,
    cost_usd NUMERIC(10,6) DEFAULT 0,
    error_message TEXT
);

CREATE INDEX idx_anchor_runs_config ON anchor_runs (anchor_config_id, started_at DESC);

CREATE TABLE IF NOT EXISTS signal_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchor_config_id UUID NOT NULL REFERENCES anchor_configs(id) ON DELETE CASCADE,
    niche_keyword TEXT NOT NULL,
    cbsa_code TEXT NOT NULL,
    snapshot_date DATE NOT NULL,

    serp_avg_da_top5 NUMERIC,
    serp_aggregator_count INTEGER,
    serp_local_biz_count INTEGER,
    serp_aio_present BOOLEAN,
    serp_local_pack_present BOOLEAN,

    local_pack_review_avg NUMERIC,
    local_pack_review_max INTEGER,
    local_pack_review_velocity NUMERIC,

    keyword_volume_total INTEGER,
    keyword_cpc_avg NUMERIC,

    observation_ids JSONB NOT NULL,

    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(anchor_config_id, snapshot_date)
);

CREATE INDEX idx_snapshots_niche_metro ON signal_snapshots (niche_keyword, cbsa_code, snapshot_date);
