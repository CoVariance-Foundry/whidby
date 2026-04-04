-- 002_experiment_schema.sql
-- Tables for the outreach experiment framework (M10-M15)

CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL CHECK (status IN (
        'draft', 'discovery', 'scanning', 'generating',
        'sending', 'tracking', 'analysis', 'closed'
    )) DEFAULT 'draft',
    niche_keyword TEXT NOT NULL,
    cbsa_code TEXT NOT NULL,
    cbsa_name TEXT,
    sample_size INT NOT NULL DEFAULT 100,
    business_filters JSONB,
    variants JSONB,
    results JSONB,
    rentability_signal JSONB
);

CREATE INDEX idx_experiments_status ON experiments (status);
CREATE INDEX idx_experiments_niche ON experiments (niche_keyword, cbsa_code);

CREATE TABLE IF NOT EXISTS experiment_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    variant_id TEXT NOT NULL,
    name TEXT,
    audit_depth TEXT CHECK (audit_depth IN ('minimal', 'standard', 'visual_mockup')),
    email_template TEXT,
    value_prop TEXT,
    allocation_pct NUMERIC,
    UNIQUE(experiment_id, variant_id)
);

CREATE TABLE IF NOT EXISTS experiment_businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    variant_id TEXT,
    business_data JSONB NOT NULL,
    contact JSONB,
    qualification_status TEXT DEFAULT 'pending',
    scan_results JSONB,
    weakness_score INT,
    quality_bucket TEXT,
    audit_url TEXT,
    outreach_status TEXT DEFAULT 'pending',
    engagement_score INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_exp_businesses_experiment ON experiment_businesses (experiment_id);
CREATE INDEX idx_exp_businesses_status ON experiment_businesses (outreach_status);

CREATE TABLE IF NOT EXISTS outreach_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    business_id UUID NOT NULL REFERENCES experiment_businesses(id) ON DELETE CASCADE,
    variant_id TEXT,
    event_type TEXT NOT NULL,
    event_data JSONB,
    metadata JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_outreach_events_experiment ON outreach_events (experiment_id);
CREATE INDEX idx_outreach_events_business ON outreach_events (business_id);
CREATE INDEX idx_outreach_events_type ON outreach_events (event_type);

CREATE TABLE IF NOT EXISTS reply_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES outreach_events(id) ON DELETE CASCADE,
    business_id UUID NOT NULL REFERENCES experiment_businesses(id) ON DELETE CASCADE,
    reply_text TEXT,
    classification TEXT,
    confidence NUMERIC,
    key_phrases JSONB,
    classified_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rentability_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche_keyword TEXT NOT NULL,
    cbsa_code TEXT NOT NULL,
    experiment_id UUID REFERENCES experiments(id),
    sample_size INT,
    response_rate NUMERIC,
    positive_intent_rate NUMERIC,
    engagement_avg NUMERIC,
    rentability_score INT,
    confidence TEXT,
    segment_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(niche_keyword, cbsa_code)
);

CREATE INDEX idx_rentability_niche ON rentability_signals (niche_keyword, cbsa_code);
