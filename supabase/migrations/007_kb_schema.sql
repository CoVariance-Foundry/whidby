-- 007_kb_schema.sql
-- Knowledge base tables for durable geo+industry intelligence.
--
-- kb_entities: canonical niche+geo identity (one row per unique industry+location pair).
-- kb_snapshots: versioned derived-state snapshots with explicit supersedence.
-- kb_evidence_artifacts: raw M5 collection payloads linked to snapshots.
-- api_response_cache: persistent cross-run DataForSEO response cache.
-- feedback_events: runtime feedback linked to snapshots and reports.

-- Canonical industry+geo entities
CREATE TABLE IF NOT EXISTS kb_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    niche_keyword_normalized TEXT NOT NULL,
    geo_target_normalized TEXT NOT NULL,
    place_id TEXT,
    dataforseo_location_code INT,
    cbsa_code TEXT,
    geo_scope TEXT NOT NULL DEFAULT 'city',
    country_iso_code TEXT NOT NULL DEFAULT 'US',
    normalization_metadata JSONB,
    UNIQUE (niche_keyword_normalized, geo_target_normalized, geo_scope)
);

CREATE INDEX idx_kb_entities_niche ON kb_entities (niche_keyword_normalized);
CREATE INDEX idx_kb_entities_geo ON kb_entities (geo_target_normalized);
CREATE INDEX idx_kb_entities_place ON kb_entities (place_id) WHERE place_id IS NOT NULL;
CREATE INDEX idx_kb_entities_dfs ON kb_entities (dataforseo_location_code) WHERE dataforseo_location_code IS NOT NULL;

-- Versioned derived-state snapshots
CREATE TABLE IF NOT EXISTS kb_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES kb_entities(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to TIMESTAMPTZ,
    is_current BOOLEAN NOT NULL DEFAULT true,
    superseded_by UUID REFERENCES kb_snapshots(id),
    input_hash TEXT NOT NULL,
    strategy_profile TEXT NOT NULL DEFAULT 'balanced',
    spec_version TEXT NOT NULL DEFAULT '1.1',
    keyword_expansion JSONB,
    signals JSONB,
    scores JSONB,
    classification JSONB,
    guidance JSONB,
    meta JSONB,
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX idx_kb_snapshots_current
    ON kb_snapshots (entity_id)
    WHERE is_current = true;

CREATE INDEX idx_kb_snapshots_entity ON kb_snapshots (entity_id, version DESC);
CREATE INDEX idx_kb_snapshots_report ON kb_snapshots (report_id) WHERE report_id IS NOT NULL;
CREATE INDEX idx_kb_snapshots_input_hash ON kb_snapshots (input_hash);

-- Raw M5 collection evidence artifacts
CREATE TABLE IF NOT EXISTS kb_evidence_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_id UUID NOT NULL REFERENCES kb_snapshots(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    artifact_type TEXT NOT NULL CHECK (artifact_type IN (
        'raw_collection', 'keyword_expansion', 'signal_bundle', 'score_bundle'
    )),
    payload JSONB NOT NULL,
    payload_hash TEXT NOT NULL,
    source_window_start TIMESTAMPTZ,
    source_window_end TIMESTAMPTZ,
    byte_size INT
);

CREATE INDEX idx_kb_evidence_snapshot ON kb_evidence_artifacts (snapshot_id);
CREATE INDEX idx_kb_evidence_type ON kb_evidence_artifacts (artifact_type);

-- Persistent cross-run API response cache
CREATE TABLE IF NOT EXISTS api_response_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    endpoint TEXT NOT NULL,
    params_hash TEXT NOT NULL,
    params JSONB NOT NULL,
    response_data JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    cost_usd NUMERIC NOT NULL DEFAULT 0,
    hit_count INT NOT NULL DEFAULT 0,
    last_hit_at TIMESTAMPTZ,
    UNIQUE (endpoint, params_hash)
);

CREATE INDEX idx_api_cache_lookup ON api_response_cache (endpoint, params_hash);
CREATE INDEX idx_api_cache_expires ON api_response_cache (expires_at);

-- Runtime feedback events linked to snapshots/reports
CREATE TABLE IF NOT EXISTS feedback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    report_id UUID REFERENCES reports(id) ON DELETE SET NULL,
    snapshot_id UUID REFERENCES kb_snapshots(id) ON DELETE SET NULL,
    entity_id UUID REFERENCES kb_entities(id) ON DELETE SET NULL,
    context JSONB NOT NULL,
    signals JSONB NOT NULL,
    scores JSONB NOT NULL,
    classification JSONB NOT NULL,
    recommendation_rank INT,
    outcome JSONB
);

CREATE INDEX idx_feedback_events_report ON feedback_events (report_id) WHERE report_id IS NOT NULL;
CREATE INDEX idx_feedback_events_snapshot ON feedback_events (snapshot_id) WHERE snapshot_id IS NOT NULL;
CREATE INDEX idx_feedback_events_entity ON feedback_events (entity_id) WHERE entity_id IS NOT NULL;
