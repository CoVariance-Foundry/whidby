-- 011_data_provider_tables.sql
--
-- Phase 7 provider persistence that does not duplicate the benchmark schema.
-- Canonical demographics live in public.metros.
-- Canonical CBP business density lives in public.census_cbp_establishments.

CREATE TABLE IF NOT EXISTS public.service_acv_estimates (
    naics_code TEXT NOT NULL REFERENCES public.census_target_naics(naics_code),
    cbsa_code TEXT NOT NULL DEFAULT 'national',
    mean_hourly_wage NUMERIC,
    avg_job_hours NUMERIC,
    overhead_multiplier NUMERIC NOT NULL DEFAULT 2.0,
    acv_estimate NUMERIC,
    year INTEGER,
    source TEXT NOT NULL DEFAULT 'bls'
        CHECK (source IN ('bls', 'manual', 'derived')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (naics_code, cbsa_code)
);

CREATE INDEX IF NOT EXISTS idx_service_acv_cbsa
    ON public.service_acv_estimates(cbsa_code);

ALTER TABLE public.service_acv_estimates ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS service_acv_read_all ON public.service_acv_estimates;
CREATE POLICY service_acv_read_all
    ON public.service_acv_estimates
    FOR SELECT
    USING (true);

COMMENT ON TABLE public.service_acv_estimates IS
    'Phase 7 BLS-derived service annual contract value estimates keyed by NAICS and CBSA. Demographics and CBP density remain in metros/census_cbp_establishments.';
