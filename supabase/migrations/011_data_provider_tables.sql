-- Phase 7: Reference tables for data providers
-- Census ACS demographics, CBP business patterns, BLS ACV estimates

-- Cities reference table (Census ACS)
CREATE TABLE IF NOT EXISTS cities (
    city_id TEXT PRIMARY KEY,
    cbsa_code TEXT UNIQUE,
    name TEXT NOT NULL,
    state TEXT,
    population INTEGER,
    median_income NUMERIC,
    homeownership_rate NUMERIC,
    housing_age_median NUMERIC,
    broadband_penetration NUMERIC,
    growth_rate NUMERIC,
    archetype TEXT,
    demographics JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cities_population ON cities(population);
CREATE INDEX IF NOT EXISTS idx_cities_state ON cities(state);
CREATE INDEX IF NOT EXISTS idx_cities_archetype ON cities(archetype);

-- Business patterns (Census CBP)
CREATE TABLE IF NOT EXISTS business_patterns (
    cbsa_code TEXT NOT NULL,
    naics_code TEXT NOT NULL,
    year INTEGER NOT NULL,
    establishments INTEGER,
    employees INTEGER,
    payroll_thousands INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (cbsa_code, naics_code, year)
);

CREATE INDEX IF NOT EXISTS idx_bp_cbsa ON business_patterns(cbsa_code);
CREATE INDEX IF NOT EXISTS idx_bp_naics ON business_patterns(naics_code);

-- Service ACV estimates (BLS wages)
CREATE TABLE IF NOT EXISTS service_acv_estimates (
    naics_code TEXT NOT NULL,
    cbsa_code TEXT DEFAULT 'national',
    mean_hourly_wage NUMERIC,
    avg_job_hours NUMERIC,
    overhead_multiplier NUMERIC DEFAULT 2.0,
    acv_estimate NUMERIC,
    year INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (naics_code, cbsa_code)
);
