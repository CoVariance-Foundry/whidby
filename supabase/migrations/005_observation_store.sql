-- 005_observation_store.sql
-- Observation store: immutable index of every DataForSEO API response.
-- Full payloads stored in Supabase Storage; this table is the fast-lookup metadata layer.

CREATE TABLE IF NOT EXISTS observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    endpoint TEXT NOT NULL,
    query_params JSONB NOT NULL,
    query_hash TEXT NOT NULL,

    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source TEXT NOT NULL DEFAULT 'pipeline'
        CHECK (source IN ('pipeline', 'anchor', 'manual')),
    run_id UUID,

    cost_usd NUMERIC(10,6) NOT NULL DEFAULT 0,
    api_queue_mode TEXT,

    storage_path TEXT,
    payload_size_bytes INTEGER,

    ttl_category TEXT NOT NULL
        CHECK (ttl_category IN ('serp', 'keyword', 'business', 'review', 'technical', 'reference')),
    expires_at TIMESTAMPTZ NOT NULL,

    status TEXT NOT NULL DEFAULT 'ok'
        CHECK (status IN ('ok', 'error', 'partial')),
    error_message TEXT,

    payload_purged BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX idx_obs_hash_fresh ON observations (query_hash, expires_at DESC);
CREATE INDEX idx_obs_hash_time ON observations (query_hash, observed_at DESC);
CREATE INDEX idx_obs_source_time ON observations (source, observed_at);
CREATE INDEX idx_obs_expires ON observations (expires_at);
