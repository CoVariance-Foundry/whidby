-- 20260524133000_whi126_benchmark_lineage.sql
--
-- WHI-126: benchmark run lineage and metric-level sufficiency.
-- Adds nullable/backfillable lineage fields without recomputing benchmarks.

CREATE TABLE IF NOT EXISTS public.seo_benchmark_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_slug TEXT UNIQUE,
    formula_version TEXT NOT NULL DEFAULT '2.0',
    sample_frame_version TEXT NOT NULL DEFAULT 'coverage-hardening-v1',
    source_window_start DATE,
    source_window_end DATE,
    source_mix JSONB NOT NULL DEFAULT '{}'::jsonb,
    acquisition_flags JSONB NOT NULL DEFAULT '{}'::jsonb,
    benchmark_mode TEXT NOT NULL DEFAULT 'exact'
        CHECK (
            benchmark_mode IN (
                'exact',
                'pooled_population',
                'pooled_service_group',
                'global_service',
                'manual'
            )
        ),
    pool_definition JSONB NOT NULL DEFAULT '{}'::jsonb,
    recomputed_at TIMESTAMPTZ,
    cost_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.seo_benchmarks
    ADD COLUMN IF NOT EXISTS benchmark_run_id UUID
        REFERENCES public.seo_benchmark_runs(id),
    ADD COLUMN IF NOT EXISTS benchmark_mode TEXT NOT NULL DEFAULT 'exact',
    ADD COLUMN IF NOT EXISTS formula_version TEXT,
    ADD COLUMN IF NOT EXISTS sample_frame_version TEXT,
    ADD COLUMN IF NOT EXISTS metric_confidence_rollup JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE public.seo_benchmarks
    ADD CONSTRAINT seo_benchmarks_benchmark_mode_check
    CHECK (
        benchmark_mode IN (
            'exact',
            'pooled_population',
            'pooled_service_group',
            'global_service',
            'manual'
        )
    );

CREATE TABLE IF NOT EXISTS public.seo_benchmark_metric_sufficiency (
    benchmark_run_id UUID NOT NULL
        REFERENCES public.seo_benchmark_runs(id) ON DELETE CASCADE,
    niche_normalized TEXT NOT NULL,
    population_class TEXT NOT NULL,
    metric_family TEXT NOT NULL
        CHECK (
            metric_family IN (
                'demand',
                'organic_serp',
                'organic_authority',
                'lighthouse_site_quality',
                'local_pack',
                'review_velocity',
                'gbp_profile',
                'monetization',
                'ai_serp_displacement'
            )
        ),
    attempted_metros INTEGER NOT NULL DEFAULT 0 CHECK (attempted_metros >= 0),
    non_null_metros INTEGER NOT NULL DEFAULT 0 CHECK (non_null_metros >= 0),
    attempted_observations INTEGER NOT NULL DEFAULT 0 CHECK (attempted_observations >= 0),
    non_null_observations INTEGER NOT NULL DEFAULT 0 CHECK (non_null_observations >= 0),
    confidence_label TEXT NOT NULL
        CHECK (confidence_label IN ('high', 'medium', 'low', 'insufficient')),
    source_endpoint TEXT,
    source_window_start DATE,
    source_window_end DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (
        benchmark_run_id,
        niche_normalized,
        population_class,
        metric_family
    ),
    FOREIGN KEY (niche_normalized, population_class)
        REFERENCES public.seo_benchmarks(niche_normalized, population_class)
        ON DELETE CASCADE,
    CHECK (non_null_metros <= attempted_metros),
    CHECK (non_null_observations <= attempted_observations)
);

CREATE INDEX IF NOT EXISTS idx_seo_benchmark_runs_slug
    ON public.seo_benchmark_runs(run_slug);
CREATE INDEX IF NOT EXISTS idx_seo_benchmarks_run
    ON public.seo_benchmarks(benchmark_run_id);
CREATE INDEX IF NOT EXISTS idx_seo_benchmark_metric_sufficiency_cell
    ON public.seo_benchmark_metric_sufficiency(niche_normalized, population_class);
CREATE INDEX IF NOT EXISTS idx_seo_benchmark_metric_sufficiency_family
    ON public.seo_benchmark_metric_sufficiency(metric_family);

ALTER TABLE public.seo_benchmark_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seo_benchmark_metric_sufficiency ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS benchmark_runs_read_all ON public.seo_benchmark_runs;
CREATE POLICY benchmark_runs_read_all
    ON public.seo_benchmark_runs
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS benchmark_metric_sufficiency_read_all
    ON public.seo_benchmark_metric_sufficiency;
CREATE POLICY benchmark_metric_sufficiency_read_all
    ON public.seo_benchmark_metric_sufficiency
    FOR SELECT
    USING (true);

COMMENT ON TABLE public.seo_benchmark_runs IS
    'Lineage for benchmark recompute/acquisition batches, including formula version, sample frame, source mix, pooling mode, recompute time, and cost summary.';
COMMENT ON TABLE public.seo_benchmark_metric_sufficiency IS
    'Metric-family sufficiency evidence for each benchmark run and benchmark cell.';
COMMENT ON COLUMN public.seo_benchmarks.benchmark_run_id IS
    'Nullable link to the benchmark run that produced or validated this benchmark cell.';
COMMENT ON COLUMN public.seo_benchmarks.metric_confidence_rollup IS
    'JSON rollup mapping metric families to confidence/evidence summaries used by the aggregate confidence label.';
