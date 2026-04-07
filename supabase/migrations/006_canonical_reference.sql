-- 006_canonical_reference.sql
-- Canonical reference store: metros, benchmarks, and niche taxonomies.

CREATE TABLE IF NOT EXISTS canonical_metros (
    cbsa_code TEXT PRIMARY KEY,
    cbsa_name TEXT NOT NULL,
    state TEXT NOT NULL,
    region TEXT NOT NULL,
    population INTEGER NOT NULL,
    population_year INTEGER NOT NULL,
    population_growth_pct NUMERIC(5,2),
    principal_cities JSONB NOT NULL,
    dataforseo_location_codes JSONB NOT NULL,
    metro_size_tier TEXT NOT NULL
        CHECK (metro_size_tier IN ('major', 'mid', 'small')),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS canonical_benchmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche_keyword TEXT NOT NULL,
    metro_size_tier TEXT,
    metric_name TEXT NOT NULL,
    metric_value NUMERIC NOT NULL,
    sample_size INTEGER NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_until TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL DEFAULT 'computed'
        CHECK (source IN ('computed', 'external')),
    UNIQUE(niche_keyword, metro_size_tier, metric_name)
);

CREATE TABLE IF NOT EXISTS canonical_niches (
    niche_keyword TEXT PRIMARY KEY,
    dataforseo_category TEXT,
    parent_vertical TEXT,
    requires_physical_fulfillment BOOLEAN DEFAULT true,
    typical_aio_exposure TEXT,
    modifier_patterns JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
