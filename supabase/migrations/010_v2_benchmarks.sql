-- 010_v2_benchmarks.sql
--
-- V2 scoring schema additions:
--   1. metros.population_class                  — derived bucket for benchmarking
--   2. metro_location_cache                     — populated from metros (autocomplete)
--   3. niche_naics_mapping                      — bridge: niche keyword → NAICS code(s)
--   4. seo_facts                                — denormalized keyword-level observations
--   5. seo_benchmarks                           — aggregations over seo_facts (per niche × pop class)
--   6. metro_score_v2                           — V2 score output (vector of dimensions, no composite)
--
-- Design notes:
-- - V2 abandons the composite opportunity score. metro_score_v2 has nullable
--   local_difficulty (set to NULL when no local pack present, not a fixed 75).
-- - Benchmarks store p25/median/p75 + sample_size; V2 scoring uses median as
--   the green threshold and the IQR for spread context.
-- - confidence_label degrades gracefully: 'high' (n>=20), 'medium' (n>=8),
--   'low' (n>=3), 'insufficient' (n<3). V2 surfaces this in the UI so users
--   know when a cell is thin.

-- ============================================================
-- 1. metros.population_class
-- ============================================================

ALTER TABLE public.metros
  ADD COLUMN IF NOT EXISTS population_class TEXT;

-- Population class buckets (Coral's mental model from the call:
-- "city of 60K vs 300K vs metro" — coarse enough to pool samples,
-- fine enough to differentiate)
UPDATE public.metros
SET population_class = CASE
    WHEN population IS NULL THEN NULL
    WHEN population < 50000 THEN 'micro_under_50k'
    WHEN population < 100000 THEN 'small_50_100k'
    WHEN population < 300000 THEN 'medium_100_300k'
    WHEN population < 1000000 THEN 'large_300k_1m'
    WHEN population < 5000000 THEN 'metro_1m_5m'
    ELSE 'mega_5m_plus'
END;

CREATE INDEX IF NOT EXISTS idx_metros_pop_class ON public.metros(population_class);

-- ============================================================
-- 2. metro_location_cache: backfill from metros for autocomplete
-- ============================================================

-- Add normalized search column for fast prefix matching
ALTER TABLE public.metro_location_cache
  ADD COLUMN IF NOT EXISTS search_label TEXT,
  ADD COLUMN IF NOT EXISTS normalized_label TEXT,
  ADD COLUMN IF NOT EXISTS population_class TEXT,
  ADD COLUMN IF NOT EXISTS owner_occupancy_rate NUMERIC(5,4);

-- Repopulate from metros (truncate + insert keeps logic simple; cache is small)
TRUNCATE public.metro_location_cache;

INSERT INTO public.metro_location_cache (
    cbsa_code, cbsa_name, state, population,
    principal_cities, dataforseo_location_codes,
    search_label, normalized_label, population_class, owner_occupancy_rate
)
SELECT
    cbsa_code, cbsa_name, state, population,
    to_jsonb(principal_cities), to_jsonb(dataforseo_location_codes),
    cbsa_name AS search_label,
    lower(regexp_replace(cbsa_name, '[^a-zA-Z0-9 ]', '', 'g')) AS normalized_label,
    population_class,
    owner_occupancy_rate
FROM public.metros;

CREATE INDEX IF NOT EXISTS idx_mlc_normalized
    ON public.metro_location_cache USING gin (normalized_label gin_trgm_ops);

-- Required extension for trigram fast prefix/substring matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- 3. niche_naics_mapping
-- ============================================================
-- Many-to-many: a niche can map to multiple NAICS (e.g., "HVAC" = 238220 + 238210),
-- and a NAICS can match multiple niches. weight sums to 1 within a niche.

CREATE TABLE IF NOT EXISTS public.niche_naics_mapping (
    niche_keyword     TEXT NOT NULL,
    niche_normalized  TEXT NOT NULL,
    naics_code        TEXT NOT NULL REFERENCES public.census_target_naics(naics_code),
    weight            NUMERIC(4,3) NOT NULL DEFAULT 1.0,
    is_primary        BOOLEAN NOT NULL DEFAULT TRUE,
    source            TEXT NOT NULL DEFAULT 'manual'
        CHECK (source IN ('manual', 'llm', 'derived', 'tag_match')),
    confidence        NUMERIC(4,3) NOT NULL DEFAULT 1.0,
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (niche_normalized, naics_code)
);

CREATE INDEX IF NOT EXISTS idx_nnm_niche ON public.niche_naics_mapping(niche_normalized);
CREATE INDEX IF NOT EXISTS idx_nnm_naics ON public.niche_naics_mapping(naics_code);

-- Bootstrap mappings from census_target_niche_tags (each tag → one NAICS)
INSERT INTO public.niche_naics_mapping (niche_keyword, niche_normalized, naics_code, source, confidence, weight, is_primary)
SELECT
    UNNEST(niche_tags) AS niche_keyword,
    lower(UNNEST(niche_tags)) AS niche_normalized,
    naics_code,
    'tag_match',
    0.9,
    1.0,
    TRUE
FROM public.census_target_naics
ON CONFLICT (niche_normalized, naics_code) DO NOTHING;

-- ============================================================
-- 4. seo_facts: denormalized keyword-level observations
-- ============================================================
-- Grain: (niche_normalized, cbsa_code, keyword, snapshot_date)
-- Decoupled from reports so benchmarks don't depend on report retention.
-- Backfilled from report_keywords + populated forward from new scoring runs.

CREATE TABLE IF NOT EXISTS public.seo_facts (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche_keyword     TEXT NOT NULL,
    niche_normalized  TEXT NOT NULL,
    cbsa_code         TEXT NOT NULL REFERENCES public.metros(cbsa_code),
    keyword           TEXT NOT NULL,
    keyword_tier      INTEGER CHECK (keyword_tier IN (1, 2, 3)),
    intent            TEXT CHECK (intent IN ('transactional', 'commercial', 'informational')),

    -- Demand signals
    search_volume_monthly  INTEGER,
    cpc_usd                NUMERIC(10,2),

    -- SERP features observed for this keyword in this metro
    aio_present                BOOLEAN,
    local_pack_present         BOOLEAN,
    local_pack_position        INTEGER,
    aggregator_count_top10     INTEGER,
    local_biz_count_top10      INTEGER,
    featured_snippet_present   BOOLEAN,
    paa_count                  INTEGER,
    ads_present                BOOLEAN,
    lsa_present                BOOLEAN,

    -- Top local pack signals (for local difficulty benchmarking)
    top3_review_count_min      INTEGER,  -- the floor — bar to clear
    top3_review_count_avg      INTEGER,
    top3_review_velocity_avg   NUMERIC(6,2),  -- reviews/month
    top3_rating_avg            NUMERIC(3,2),

    -- Provenance
    snapshot_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    report_id         UUID REFERENCES public.reports(id),
    source            TEXT NOT NULL DEFAULT 'orchestrator'
        CHECK (source IN ('orchestrator', 'backfill', 'manual', 'cache_replay')),

    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Idempotency: one fact per (niche, metro, keyword, date)
    UNIQUE (niche_normalized, cbsa_code, keyword, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_facts_niche_metro ON public.seo_facts(niche_normalized, cbsa_code);
CREATE INDEX IF NOT EXISTS idx_facts_niche_date ON public.seo_facts(niche_normalized, snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_facts_metro ON public.seo_facts(cbsa_code);

-- ============================================================
-- 5. seo_benchmarks: per (niche × population_class) aggregations
-- ============================================================
-- The artifact V2 scoring reads from. Recomputed on a schedule (or on-demand).

CREATE TABLE IF NOT EXISTS public.seo_benchmarks (
    niche_normalized   TEXT NOT NULL,
    naics_code         TEXT REFERENCES public.census_target_naics(naics_code),
    population_class   TEXT NOT NULL,

    -- Demand benchmarks (transactional + commercial volume only — per Coral)
    p25_total_volume_per_capita    NUMERIC(10,6),
    median_total_volume_per_capita NUMERIC(10,6),
    p75_total_volume_per_capita    NUMERIC(10,6),
    p25_avg_cpc                    NUMERIC(10,2),
    median_avg_cpc                 NUMERIC(10,2),
    p75_avg_cpc                    NUMERIC(10,2),

    -- Local difficulty benchmarks (only computed where local_pack_present=true)
    median_top3_review_count_min   INTEGER,
    median_top3_review_velocity    NUMERIC(6,2),
    pct_with_local_pack            NUMERIC(5,4),  -- 0-1 fraction

    -- Organic difficulty benchmarks
    median_aggregator_count        NUMERIC(4,2),
    median_local_biz_count         NUMERIC(4,2),

    -- Monetization benchmarks
    median_establishments_per_100k NUMERIC(8,2),  -- from CBP, joined to ACS pop
    median_lsa_present_rate        NUMERIC(5,4),
    median_ads_present_rate        NUMERIC(5,4),

    -- AI resilience benchmarks
    median_aio_trigger_rate        NUMERIC(5,4),

    -- Sample size + confidence
    sample_size_metros             INTEGER NOT NULL,
    sample_size_observations       INTEGER NOT NULL,
    confidence_label               TEXT NOT NULL CHECK (confidence_label IN
        ('high', 'medium', 'low', 'insufficient')),

    -- Lineage
    last_recomputed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fact_window_start              DATE,
    fact_window_end                DATE,

    PRIMARY KEY (niche_normalized, population_class)
);

-- ============================================================
-- 6. metro_score_v2: vector-of-scores output (no composite)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.metro_score_v2 (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id                UUID REFERENCES public.reports(id) ON DELETE CASCADE,
    niche_normalized         TEXT NOT NULL,
    cbsa_code                TEXT NOT NULL REFERENCES public.metros(cbsa_code),

    -- Each dimension: scored as a benchmark-relative value
    --   demand_strength: 0-200 (100 = median, 200 = 2x median)
    --   organic_difficulty: 0-100 where higher = harder (matches Ahrefs/Moz convention)
    --   local_difficulty: nullable when local_pack_present=false
    --   monetization_signal: 0-200 (per-capita normalized)
    --   ai_resilience: 0-100 (V1.1 logic preserved — Coral validated)
    demand_strength          INTEGER,
    organic_difficulty       INTEGER,
    local_difficulty         INTEGER,  -- nullable
    monetization_signal      INTEGER,
    ai_resilience            INTEGER,

    -- Direction labels — UI uses these to pick green/red without ambiguity
    demand_strength_higher_is_better       BOOLEAN NOT NULL DEFAULT TRUE,
    organic_difficulty_higher_is_better    BOOLEAN NOT NULL DEFAULT FALSE,
    local_difficulty_higher_is_better      BOOLEAN NOT NULL DEFAULT FALSE,
    monetization_signal_higher_is_better   BOOLEAN NOT NULL DEFAULT TRUE,
    ai_resilience_higher_is_better         BOOLEAN NOT NULL DEFAULT TRUE,

    -- Benchmark provenance: which benchmark cell did we score against?
    benchmark_population_class   TEXT,
    benchmark_confidence         TEXT,
    benchmark_sample_size        INTEGER,

    -- Diagnostic flags (UI hints)
    no_local_pack_detected       BOOLEAN NOT NULL DEFAULT FALSE,
    benchmark_undersampled       BOOLEAN NOT NULL DEFAULT FALSE,
    cbp_data_missing             BOOLEAN NOT NULL DEFAULT FALSE,

    -- SERP archetype + AI exposure preserved from V1.1
    serp_archetype               TEXT,
    ai_exposure                  TEXT,

    spec_version                 TEXT NOT NULL DEFAULT '2.0',
    scored_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_score_v2_report ON public.metro_score_v2(report_id);
CREATE INDEX IF NOT EXISTS idx_score_v2_niche_metro ON public.metro_score_v2(niche_normalized, cbsa_code);

-- ============================================================
-- 7. RLS — read-only public access
-- ============================================================

ALTER TABLE public.niche_naics_mapping ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seo_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seo_benchmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.metro_score_v2 ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS nnm_read_all ON public.niche_naics_mapping;
CREATE POLICY nnm_read_all ON public.niche_naics_mapping FOR SELECT USING (true);

DROP POLICY IF EXISTS facts_read_all ON public.seo_facts;
CREATE POLICY facts_read_all ON public.seo_facts FOR SELECT USING (true);

DROP POLICY IF EXISTS bench_read_all ON public.seo_benchmarks;
CREATE POLICY bench_read_all ON public.seo_benchmarks FOR SELECT USING (true);

DROP POLICY IF EXISTS score_v2_read_all ON public.metro_score_v2;
CREATE POLICY score_v2_read_all ON public.metro_score_v2 FOR SELECT USING (true);

-- ============================================================
-- Comments / documentation
-- ============================================================

COMMENT ON COLUMN public.metros.population_class IS
    'Coarse bucket used for benchmark pooling. micro<50K, small<100K, medium<300K, large<1M, metro<5M, mega>=5M.';

COMMENT ON TABLE public.niche_naics_mapping IS
    'Many-to-many bridge: user-typed niche keyword → NAICS code(s). Bootstrapped from census_target_naics.niche_tags.';

COMMENT ON TABLE public.seo_facts IS
    'Keyword-grain market observations. Decoupled from reports (which can be archived). Source for seo_benchmarks aggregation.';

COMMENT ON TABLE public.seo_benchmarks IS
    'V2 scoring benchmarks: per (niche × population_class) p25/median/p75 with sample size + confidence label. Recomputed periodically.';

COMMENT ON TABLE public.metro_score_v2 IS
    'V2 scoring output. Vector of 5 dimensions, no composite. Each dimension carries explicit direction (higher_is_better) so UI never has to interpret.';
