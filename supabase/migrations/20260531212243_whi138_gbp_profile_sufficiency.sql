-- 20260531212243_whi138_gbp_profile_sufficiency.sql
--
-- WHI-138: include real Google Business Profile completeness evidence in
-- benchmark metric-family sufficiency rows. The evidence source is the
-- canonical local-pack listing fact grain; missing gbp_completeness remains
-- missing/undersampled and must not be inferred from local-pack presence.

CREATE OR REPLACE FUNCTION public.recompute_seo_benchmarks(p_window_days INTEGER DEFAULT 90)
RETURNS TABLE (
    cells_recomputed INTEGER,
    fact_window_start DATE,
    fact_window_end DATE
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_started_at TIMESTAMPTZ := now();
    v_run_id UUID;
    v_cells INTEGER;
    v_start DATE;
    v_end DATE;
BEGIN
    INSERT INTO public.seo_benchmark_runs (
        run_slug,
        formula_version,
        sample_frame_version,
        source_mix,
        acquisition_flags,
        benchmark_mode,
        pool_definition,
        recomputed_at
    )
    VALUES (
        'recompute-' || to_char(v_started_at, 'YYYYMMDDHH24MISSMS'),
        '2.0',
        'coverage-hardening-v1',
        jsonb_build_object(
            'seo_facts', true,
            'local_pack_listing_facts', true,
            'census_cbp_establishments', true
        ),
        jsonb_build_object('window_days', p_window_days),
        'exact',
        '{}'::jsonb,
        v_started_at
    )
    RETURNING id INTO v_run_id;

    SELECT
        legacy.cells_recomputed,
        legacy.fact_window_start,
        legacy.fact_window_end
    INTO v_cells, v_start, v_end
    FROM public.recompute_seo_benchmarks_without_lineage(p_window_days) AS legacy;

    UPDATE public.seo_benchmark_runs
    SET
        source_window_start = v_start,
        source_window_end = v_end
    WHERE id = v_run_id;

    UPDATE public.seo_benchmarks
    SET
        benchmark_run_id = v_run_id,
        benchmark_mode = 'exact',
        formula_version = '2.0',
        sample_frame_version = 'coverage-hardening-v1',
        metric_confidence_rollup = '{}'::jsonb
    WHERE last_recomputed_at >= v_started_at;

    WITH recomputed_cells AS (
        SELECT niche_normalized, population_class
        FROM public.seo_benchmarks
        WHERE benchmark_run_id = v_run_id
    ),
    fact_base AS (
        SELECT
            f.niche_normalized,
            f.cbsa_code,
            m.population_class,
            f.search_volume_monthly,
            f.cpc_usd,
            f.aggregator_count_top10,
            f.local_biz_count_top10,
            f.avg_top5_da,
            f.avg_top5_lighthouse,
            f.local_pack_present,
            f.local_pack_position,
            f.top3_review_count_min,
            f.top3_review_velocity_avg,
            f.aio_present,
            f.featured_snippet_present,
            f.paa_count,
            f.lsa_present,
            f.ads_present
        FROM public.seo_facts f
        JOIN public.metros m USING (cbsa_code)
        JOIN recomputed_cells rc
          ON rc.niche_normalized = f.niche_normalized
         AND rc.population_class = m.population_class
        WHERE f.intent IN ('transactional', 'commercial')
          AND f.snapshot_date >= v_start
          AND m.population_class IS NOT NULL
          AND m.population IS NOT NULL
    ),
    local_pack_base AS (
        SELECT
            l.niche_normalized,
            l.cbsa_code,
            m.population_class,
            l.gbp_completeness
        FROM public.local_pack_listing_facts l
        JOIN public.metros m USING (cbsa_code)
        JOIN recomputed_cells rc
          ON rc.niche_normalized = l.niche_normalized
         AND rc.population_class = m.population_class
        WHERE l.snapshot_date >= v_start
          AND l.snapshot_date <= v_end
          AND m.population_class IS NOT NULL
          AND m.population IS NOT NULL
    ),
    metric_stats AS (
        SELECT
            niche_normalized,
            population_class,
            'demand'::text AS metric_family,
            count(DISTINCT cbsa_code)::integer AS attempted_metros,
            count(DISTINCT cbsa_code) FILTER (
                WHERE search_volume_monthly IS NOT NULL
            )::integer AS non_null_metros,
            count(*)::integer AS attempted_observations,
            count(*) FILTER (
                WHERE search_volume_monthly IS NOT NULL
            )::integer AS non_null_observations,
            'keywords_data/google/search_volume/task_post'::text AS source_endpoint
        FROM fact_base
        GROUP BY niche_normalized, population_class

        UNION ALL

        SELECT
            niche_normalized,
            population_class,
            'organic_serp',
            count(DISTINCT cbsa_code)::integer,
            count(DISTINCT cbsa_code) FILTER (
                WHERE aggregator_count_top10 IS NOT NULL
                   OR local_biz_count_top10 IS NOT NULL
            )::integer,
            count(*)::integer,
            count(*) FILTER (
                WHERE aggregator_count_top10 IS NOT NULL
                   OR local_biz_count_top10 IS NOT NULL
            )::integer,
            'serp/google/organic/live/advanced'
        FROM fact_base
        GROUP BY niche_normalized, population_class

        UNION ALL

        SELECT
            niche_normalized,
            population_class,
            'organic_authority',
            count(DISTINCT cbsa_code)::integer,
            count(DISTINCT cbsa_code) FILTER (WHERE avg_top5_da IS NOT NULL)::integer,
            count(*)::integer,
            count(*) FILTER (WHERE avg_top5_da IS NOT NULL)::integer,
            'backlinks/summary/live'
        FROM fact_base
        GROUP BY niche_normalized, population_class

        UNION ALL

        SELECT
            niche_normalized,
            population_class,
            'lighthouse_site_quality',
            count(DISTINCT cbsa_code)::integer,
            count(DISTINCT cbsa_code) FILTER (WHERE avg_top5_lighthouse IS NOT NULL)::integer,
            count(*)::integer,
            count(*) FILTER (WHERE avg_top5_lighthouse IS NOT NULL)::integer,
            'on_page/lighthouse/live/json'
        FROM fact_base
        GROUP BY niche_normalized, population_class

        UNION ALL

        SELECT
            niche_normalized,
            population_class,
            'local_pack',
            count(DISTINCT cbsa_code)::integer,
            count(DISTINCT cbsa_code) FILTER (
                WHERE local_pack_present IS NOT NULL
                   OR local_pack_position IS NOT NULL
                   OR top3_review_count_min IS NOT NULL
            )::integer,
            count(*)::integer,
            count(*) FILTER (
                WHERE local_pack_present IS NOT NULL
                   OR local_pack_position IS NOT NULL
                   OR top3_review_count_min IS NOT NULL
            )::integer,
            'serp/google/organic/live/advanced'
        FROM fact_base
        GROUP BY niche_normalized, population_class

        UNION ALL

        SELECT
            niche_normalized,
            population_class,
            'review_velocity',
            count(DISTINCT cbsa_code)::integer,
            count(DISTINCT cbsa_code) FILTER (WHERE top3_review_velocity_avg IS NOT NULL)::integer,
            count(*)::integer,
            count(*) FILTER (WHERE top3_review_velocity_avg IS NOT NULL)::integer,
            'business_data/google/reviews/task_post'
        FROM fact_base
        GROUP BY niche_normalized, population_class

        UNION ALL

        -- GBP profile evidence lives at the local-pack listing grain rather
        -- than seo_facts. attempted_* counts therefore measure observed GBP
        -- profile evidence rows, while zero rows still roll up as insufficient.
        SELECT
            rc.niche_normalized,
            rc.population_class,
            'gbp_profile',
            count(DISTINCT lp.cbsa_code)::integer,
            count(DISTINCT lp.cbsa_code) FILTER (
                WHERE lp.gbp_completeness IS NOT NULL
            )::integer,
            count(lp.cbsa_code)::integer,
            count(lp.gbp_completeness)::integer,
            'business_data/google/my_business_info/live'
        FROM recomputed_cells rc
        LEFT JOIN local_pack_base lp
          ON lp.niche_normalized = rc.niche_normalized
         AND lp.population_class = rc.population_class
        GROUP BY rc.niche_normalized, rc.population_class

        UNION ALL

        SELECT
            niche_normalized,
            population_class,
            'monetization',
            count(DISTINCT cbsa_code)::integer,
            count(DISTINCT cbsa_code) FILTER (
                WHERE cpc_usd IS NOT NULL
                   OR lsa_present IS NOT NULL
                   OR ads_present IS NOT NULL
            )::integer,
            count(*)::integer,
            count(*) FILTER (
                WHERE cpc_usd IS NOT NULL
                   OR lsa_present IS NOT NULL
                   OR ads_present IS NOT NULL
            )::integer,
            'keywords_data/google/search_volume/task_post + serp/google/organic/live/advanced'
        FROM fact_base
        GROUP BY niche_normalized, population_class

        UNION ALL

        SELECT
            niche_normalized,
            population_class,
            'ai_serp_displacement',
            count(DISTINCT cbsa_code)::integer,
            count(DISTINCT cbsa_code) FILTER (
                WHERE aio_present IS NOT NULL
                   OR featured_snippet_present IS NOT NULL
                   OR paa_count IS NOT NULL
            )::integer,
            count(*)::integer,
            count(*) FILTER (
                WHERE aio_present IS NOT NULL
                   OR featured_snippet_present IS NOT NULL
                   OR paa_count IS NOT NULL
            )::integer,
            'serp/google/organic/live/advanced'
        FROM fact_base
        GROUP BY niche_normalized, population_class
    )
    INSERT INTO public.seo_benchmark_metric_sufficiency (
        benchmark_run_id,
        niche_normalized,
        population_class,
        metric_family,
        attempted_metros,
        non_null_metros,
        attempted_observations,
        non_null_observations,
        confidence_label,
        source_endpoint,
        source_window_start,
        source_window_end
    )
    SELECT
        v_run_id,
        ms.niche_normalized,
        ms.population_class,
        ms.metric_family,
        ms.attempted_metros,
        ms.non_null_metros,
        ms.attempted_observations,
        ms.non_null_observations,
        CASE
            WHEN ms.non_null_metros >= 20 THEN 'high'
            WHEN ms.non_null_metros >= 8 THEN 'medium'
            WHEN ms.non_null_metros >= 3 THEN 'low'
            ELSE 'insufficient'
        END AS confidence_label,
        ms.source_endpoint,
        v_start,
        v_end
    FROM metric_stats ms;

    UPDATE public.seo_benchmarks b
    SET metric_confidence_rollup = coalesce(rollup.metric_confidence_rollup, '{}'::jsonb)
    FROM (
        SELECT
            niche_normalized,
            population_class,
            jsonb_object_agg(
                metric_family,
                jsonb_build_object(
                    'confidence_label', confidence_label,
                    'attempted_metros', attempted_metros,
                    'non_null_metros', non_null_metros,
                    'attempted_observations', attempted_observations,
                    'non_null_observations', non_null_observations
                )
            ) AS metric_confidence_rollup
        FROM public.seo_benchmark_metric_sufficiency
        WHERE benchmark_run_id = v_run_id
        GROUP BY niche_normalized, population_class
    ) rollup
    WHERE b.benchmark_run_id = v_run_id
      AND b.niche_normalized = rollup.niche_normalized
      AND b.population_class = rollup.population_class;

    RETURN QUERY SELECT v_cells, v_start, v_end;
END;
$$;

REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM anon;
REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.recompute_seo_benchmarks(INTEGER) TO service_role;
