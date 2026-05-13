-- 013_sonar_slice_lite.sql
--
-- Sonar slice-lite persistence. This stores CellRecord JSON built from
-- currently available Widby benchmark tables. Full Sonar residuals remain
-- gated on geo crosswalk, NES, BDS, trends, and historical CBP inputs.

CREATE SCHEMA IF NOT EXISTS sonar;

CREATE TABLE IF NOT EXISTS sonar.cells (
    cell_id           TEXT PRIMARY KEY,
    naics_code        TEXT NOT NULL REFERENCES public.census_target_naics(naics_code),
    naics_version     TEXT NOT NULL DEFAULT 'NAICS2017',
    geo_id            TEXT NOT NULL,
    geo_level         TEXT NOT NULL CHECK (geo_level IN ('msa')),
    geo_name          TEXT NOT NULL,
    year              INTEGER NOT NULL,
    latest_run_id     UUID,
    latest_score      NUMERIC,
    latest_score_ts   TIMESTAMPTZ,
    status            TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'partial_sources', 'suppressed', 'insufficient_peers')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sonar.cell_runs (
    run_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cell_id           TEXT NOT NULL REFERENCES sonar.cells(cell_id) ON DELETE CASCADE,
    cell_record       JSONB NOT NULL,
    score             NUMERIC,
    score_version     TEXT NOT NULL DEFAULT 'sonar-lite-0.1',
    parquet_root      TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sonar.scoring_weights (
    version           TEXT PRIMARY KEY,
    weights           JSONB NOT NULL,
    notes             TEXT NOT NULL,
    active            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO sonar.scoring_weights (version, weights, notes, active)
VALUES (
    'sonar-lite-0.1',
    '{"demand_supply_tension":0.40,"commercial_intent":0.20,"monetization_headroom":0.20,"serp_entry":0.20}'::jsonb,
    'Slice-lite weights for available ACS, CBP, and DataForSEO facts. Not the full Sonar residual score.',
    TRUE
)
ON CONFLICT (version) DO UPDATE SET
    weights = EXCLUDED.weights,
    notes = EXCLUDED.notes,
    active = EXCLUDED.active;

CREATE INDEX IF NOT EXISTS idx_sonar_cells_lookup
    ON sonar.cells(naics_code, geo_level, geo_id, year);

CREATE INDEX IF NOT EXISTS idx_sonar_cell_runs_cell
    ON sonar.cell_runs(cell_id, created_at DESC);

ALTER TABLE sonar.cells ENABLE ROW LEVEL SECURITY;
ALTER TABLE sonar.cell_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE sonar.scoring_weights ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sonar_cells_service_all ON sonar.cells;
CREATE POLICY sonar_cells_service_all ON sonar.cells
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS sonar_cell_runs_service_all ON sonar.cell_runs;
CREATE POLICY sonar_cell_runs_service_all ON sonar.cell_runs
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS sonar_scoring_weights_service_all ON sonar.scoring_weights;
CREATE POLICY sonar_scoring_weights_service_all ON sonar.scoring_weights
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE OR REPLACE FUNCTION public.persist_sonar_slice_lite(p_record JSONB)
RETURNS TABLE (
    cell_id TEXT,
    run_id UUID,
    score NUMERIC,
    score_version TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    v_cell_id TEXT := p_record->>'cell_id';
    v_naics_code TEXT := p_record->>'naics_code';
    v_geo_id TEXT := p_record->>'geo_id';
    v_geo_level TEXT := p_record->>'geo_level';
    v_geo_name TEXT := p_record->>'geo_name';
    v_year INTEGER := NULLIF(p_record->>'year', '')::INTEGER;
    v_score NUMERIC := NULLIF(p_record #>> '{score,underserved_score}', '')::NUMERIC;
    v_score_version TEXT := COALESCE(
        NULLIF(p_record #>> '{score,score_version}', ''),
        'sonar-lite-0.1'
    );
    v_latest_score_ts TIMESTAMPTZ := COALESCE(
        NULLIF(p_record->>'extract_run_ts', '')::TIMESTAMPTZ,
        NOW()
    );
    v_run_id UUID;
BEGIN
    IF v_cell_id IS NULL
       OR v_naics_code IS NULL
       OR v_geo_id IS NULL
       OR v_geo_level IS NULL
       OR v_geo_name IS NULL
       OR v_year IS NULL THEN
        RAISE EXCEPTION 'p_record missing required Sonar slice-lite identity fields';
    END IF;

    INSERT INTO sonar.cells (
        cell_id,
        naics_code,
        naics_version,
        geo_id,
        geo_level,
        geo_name,
        year,
        latest_score,
        latest_score_ts,
        status
    )
    VALUES (
        v_cell_id,
        v_naics_code,
        COALESCE(NULLIF(p_record->>'naics_version', ''), 'NAICS2017'),
        v_geo_id,
        v_geo_level,
        v_geo_name,
        v_year,
        v_score,
        v_latest_score_ts,
        'partial_sources'
    )
    ON CONFLICT ON CONSTRAINT cells_pkey DO UPDATE SET
        naics_code = EXCLUDED.naics_code,
        naics_version = EXCLUDED.naics_version,
        geo_id = EXCLUDED.geo_id,
        geo_level = EXCLUDED.geo_level,
        geo_name = EXCLUDED.geo_name,
        year = EXCLUDED.year,
        latest_score = EXCLUDED.latest_score,
        latest_score_ts = EXCLUDED.latest_score_ts,
        status = EXCLUDED.status,
        updated_at = NOW();

    INSERT INTO sonar.cell_runs (
        cell_id,
        cell_record,
        score,
        score_version
    )
    VALUES (
        v_cell_id,
        p_record,
        v_score,
        v_score_version
    )
    RETURNING sonar.cell_runs.run_id INTO v_run_id;

    UPDATE sonar.cells
    SET latest_run_id = v_run_id,
        latest_score = v_score,
        latest_score_ts = v_latest_score_ts,
        updated_at = NOW()
    WHERE sonar.cells.cell_id = v_cell_id;

    RETURN QUERY SELECT v_cell_id, v_run_id, v_score, v_score_version;
END;
$$;

REVOKE ALL ON SCHEMA sonar FROM PUBLIC;
REVOKE ALL ON SCHEMA sonar FROM anon;
REVOKE ALL ON SCHEMA sonar FROM authenticated;
GRANT USAGE ON SCHEMA sonar TO service_role;

REVOKE ALL ON FUNCTION public.persist_sonar_slice_lite(JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.persist_sonar_slice_lite(JSONB) FROM anon;
REVOKE ALL ON FUNCTION public.persist_sonar_slice_lite(JSONB) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.persist_sonar_slice_lite(JSONB) TO service_role;

COMMENT ON SCHEMA sonar IS
    'Cell-level Sonar outputs. Slice-lite stores available Widby benchmark-derived records; full residuals require additional source layers.';

COMMENT ON TABLE sonar.cells IS
    'Registry for Sonar cells keyed by NAICS, geo, geo level, and year.';

COMMENT ON TABLE sonar.cell_runs IS
    'Versioned Sonar CellRecord JSONB output and score lineage.';

COMMENT ON FUNCTION public.persist_sonar_slice_lite(JSONB) IS
    'PostgREST-callable service-role RPC that persists a Sonar slice-lite CellRecord without exposing the sonar schema over REST.';
