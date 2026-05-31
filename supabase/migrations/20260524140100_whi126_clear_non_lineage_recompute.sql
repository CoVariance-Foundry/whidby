-- 20260524140100_whi126_clear_non_lineage_recompute.sql
--
-- WHI-126: keep legacy benchmark recomputes from carrying stale run lineage.

DO $$
BEGIN
    IF to_regprocedure('public.recompute_seo_benchmarks_without_lineage(integer)') IS NULL THEN
        IF to_regprocedure('public.recompute_seo_benchmarks(integer)') IS NULL THEN
            RAISE EXCEPTION 'public.recompute_seo_benchmarks(integer) must exist before WHI-126 wrapper migration';
        END IF;

        ALTER FUNCTION public.recompute_seo_benchmarks(INTEGER)
            RENAME TO recompute_seo_benchmarks_without_lineage;
    END IF;
END $$;

CREATE OR REPLACE FUNCTION public.recompute_seo_benchmarks(p_window_days INTEGER DEFAULT 90)
RETURNS TABLE (
    cells_recomputed INTEGER,
    fact_window_start DATE,
    fact_window_end DATE
)
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
DECLARE
    v_started_at TIMESTAMPTZ := now();
    v_cells INTEGER;
    v_start DATE;
    v_end DATE;
BEGIN
    SELECT
        legacy.cells_recomputed,
        legacy.fact_window_start,
        legacy.fact_window_end
    INTO v_cells, v_start, v_end
    FROM public.recompute_seo_benchmarks_without_lineage(p_window_days) AS legacy;

    UPDATE public.seo_benchmarks
    SET
        benchmark_run_id = NULL,
        benchmark_mode = 'exact',
        formula_version = NULL,
        sample_frame_version = NULL,
        metric_confidence_rollup = '{}'::jsonb
    WHERE last_recomputed_at >= v_started_at;

    RETURN QUERY SELECT v_cells, v_start, v_end;
END;
$$;

REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM anon;
REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.recompute_seo_benchmarks(INTEGER) TO service_role;
