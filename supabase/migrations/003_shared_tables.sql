-- 003_shared_tables.sql
-- Shared infrastructure tables used by multiple modules

-- API usage log — every DataForSEO call is tracked here (M0 cost tracking)
CREATE TABLE IF NOT EXISTS api_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    endpoint TEXT NOT NULL,
    task_id TEXT,
    cost NUMERIC NOT NULL DEFAULT 0,
    cached BOOLEAN NOT NULL DEFAULT false,
    latency_ms INT,
    parameters JSONB,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL
);

CREATE INDEX idx_api_usage_endpoint ON api_usage_log (endpoint);
CREATE INDEX idx_api_usage_created ON api_usage_log (created_at DESC);
CREATE INDEX idx_api_usage_report ON api_usage_log (report_id);

-- Metro cache — pre-computed DataForSEO location code mapping (M1)
CREATE TABLE IF NOT EXISTS metro_location_cache (
    cbsa_code TEXT PRIMARY KEY,
    cbsa_name TEXT NOT NULL,
    state TEXT NOT NULL,
    population INT NOT NULL,
    principal_cities JSONB,
    dataforseo_location_codes JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Global suppression list for outreach (M13)
CREATE TABLE IF NOT EXISTS suppression_list (
    email TEXT PRIMARY KEY,
    reason TEXT,
    suppressed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
