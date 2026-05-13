-- 012_recompute_seo_benchmarks.sql
--
-- Rebuilds public.seo_benchmarks from public.seo_facts.

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
    v_start DATE := CURRENT_DATE - p_window_days;
    v_end DATE;
    v_cells INTEGER;
BEGIN
    SELECT max(snapshot_date) INTO v_end
    FROM public.seo_facts
    WHERE snapshot_date >= v_start;

    WITH primary_naics AS (
        SELECT DISTINCT ON (niche_normalized)
            niche_normalized,
            naics_code
        FROM public.niche_naics_mapping
        WHERE is_primary = TRUE
        ORDER BY niche_normalized, confidence DESC, weight DESC, naics_code
    ),
    mapping_weights AS (
        SELECT
            nm.niche_normalized,
            nm.naics_code,
            coalesce(nullif(nm.weight, 0), 1.0)::numeric AS raw_weight
        FROM public.niche_naics_mapping nm
    ),
    normalized_mapping AS (
        SELECT
            mw.niche_normalized,
            mw.naics_code,
            CASE
                WHEN sum(mw.raw_weight) OVER (PARTITION BY mw.niche_normalized) > 0
                THEN mw.raw_weight / sum(mw.raw_weight) OVER (PARTITION BY mw.niche_normalized)
                ELSE 1.0
            END AS mapping_weight
        FROM mapping_weights mw
    ),
    latest_cbp_year AS (
        SELECT max(census_cbp_establishments.year) AS year
        FROM public.census_cbp_establishments
    ),
    fact_rollup AS (
        SELECT
            f.niche_normalized,
            f.cbsa_code,
            m.population_class,
            m.population,
            sum(coalesce(f.search_volume_monthly, 0)) AS total_volume,
            avg(f.cpc_usd) FILTER (WHERE f.cpc_usd IS NOT NULL) AS avg_cpc,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY f.top3_review_count_min)
                FILTER (WHERE f.local_pack_present IS TRUE AND f.top3_review_count_min IS NOT NULL)
                AS median_review_floor,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY f.top3_review_velocity_avg)
                FILTER (WHERE f.local_pack_present IS TRUE AND f.top3_review_velocity_avg IS NOT NULL)
                AS median_review_velocity,
            avg(CASE WHEN f.local_pack_present IS TRUE THEN 1.0 ELSE 0.0 END) AS local_pack_rate,
            avg(f.aggregator_count_top10) FILTER (WHERE f.aggregator_count_top10 IS NOT NULL) AS avg_aggregators,
            avg(f.local_biz_count_top10) FILTER (WHERE f.local_biz_count_top10 IS NOT NULL) AS avg_local_biz,
            avg(CASE WHEN f.lsa_present IS TRUE THEN 1.0 ELSE 0.0 END) AS lsa_rate,
            avg(CASE WHEN f.ads_present IS TRUE THEN 1.0 ELSE 0.0 END) AS ads_rate,
            avg(CASE WHEN f.aio_present IS TRUE THEN 1.0 ELSE 0.0 END) AS aio_rate,
            count(*) AS observation_count,
            min(f.snapshot_date) AS first_snapshot,
            max(f.snapshot_date) AS last_snapshot
        FROM public.seo_facts f
        JOIN public.metros m USING (cbsa_code)
        WHERE f.intent IN ('transactional', 'commercial')
          AND f.snapshot_date >= v_start
          AND m.population_class IS NOT NULL
          AND m.population IS NOT NULL
        GROUP BY f.niche_normalized, f.cbsa_code, m.population_class, m.population
    ),
    cbp_density AS (
        SELECT
            fr.niche_normalized,
            fr.cbsa_code,
            sum(coalesce(c.est, 0) * nm.mapping_weight) AS weighted_establishments
        FROM fact_rollup fr
        LEFT JOIN normalized_mapping nm
            ON nm.niche_normalized = fr.niche_normalized
        CROSS JOIN latest_cbp_year lcy
        LEFT JOIN public.census_cbp_establishments c
            ON c.cbsa_code = fr.cbsa_code
           AND c.naics_code = nm.naics_code
           AND c.year = lcy.year
        GROUP BY fr.niche_normalized, fr.cbsa_code
    ),
    rollup_with_cbp AS (
        SELECT
            fr.*,
            CASE
                WHEN fr.population > 0
                THEN (coalesce(cd.weighted_establishments, 0)::numeric / fr.population) * 100000
                ELSE NULL
            END AS establishments_per_100k
        FROM fact_rollup fr
        LEFT JOIN cbp_density cd
            ON cd.niche_normalized = fr.niche_normalized
           AND cd.cbsa_code = fr.cbsa_code
    ),
    cell_stats AS (
        SELECT
            r.niche_normalized,
            pn.naics_code,
            r.population_class,
            percentile_cont(0.25) WITHIN GROUP (
                ORDER BY (r.total_volume::numeric / nullif(r.population, 0))
            ) AS p25_total_volume_per_capita,
            percentile_cont(0.50) WITHIN GROUP (
                ORDER BY (r.total_volume::numeric / nullif(r.population, 0))
            ) AS median_total_volume_per_capita,
            percentile_cont(0.75) WITHIN GROUP (
                ORDER BY (r.total_volume::numeric / nullif(r.population, 0))
            ) AS p75_total_volume_per_capita,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY r.avg_cpc) AS p25_avg_cpc,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.avg_cpc) AS median_avg_cpc,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY r.avg_cpc) AS p75_avg_cpc,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.median_review_floor)
                FILTER (WHERE r.median_review_floor IS NOT NULL) AS median_top3_review_count_min,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.median_review_velocity)
                FILTER (WHERE r.median_review_velocity IS NOT NULL) AS median_top3_review_velocity,
            avg(r.local_pack_rate) AS pct_with_local_pack,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.avg_aggregators) AS median_aggregator_count,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.avg_local_biz) AS median_local_biz_count,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY r.establishments_per_100k)
                AS median_establishments_per_100k,
            avg(r.lsa_rate) AS median_lsa_present_rate,
            avg(r.ads_rate) AS median_ads_present_rate,
            avg(r.aio_rate) AS median_aio_trigger_rate,
            count(*) AS sample_size_metros,
            sum(r.observation_count)::integer AS sample_size_observations,
            min(r.first_snapshot) AS computed_fact_window_start,
            max(r.last_snapshot) AS computed_fact_window_end
        FROM rollup_with_cbp r
        LEFT JOIN primary_naics pn
            ON pn.niche_normalized = r.niche_normalized
        GROUP BY r.niche_normalized, pn.naics_code, r.population_class
    )
    INSERT INTO public.seo_benchmarks (
        niche_normalized,
        naics_code,
        population_class,
        p25_total_volume_per_capita,
        median_total_volume_per_capita,
        p75_total_volume_per_capita,
        p25_avg_cpc,
        median_avg_cpc,
        p75_avg_cpc,
        median_top3_review_count_min,
        median_top3_review_velocity,
        pct_with_local_pack,
        median_aggregator_count,
        median_local_biz_count,
        median_establishments_per_100k,
        median_lsa_present_rate,
        median_ads_present_rate,
        median_aio_trigger_rate,
        sample_size_metros,
        sample_size_observations,
        confidence_label,
        last_recomputed_at,
        fact_window_start,
        fact_window_end
    )
    SELECT
        cs.niche_normalized,
        cs.naics_code,
        cs.population_class,
        cs.p25_total_volume_per_capita,
        cs.median_total_volume_per_capita,
        cs.p75_total_volume_per_capita,
        cs.p25_avg_cpc,
        cs.median_avg_cpc,
        cs.p75_avg_cpc,
        cs.median_top3_review_count_min,
        cs.median_top3_review_velocity,
        cs.pct_with_local_pack,
        cs.median_aggregator_count,
        cs.median_local_biz_count,
        cs.median_establishments_per_100k,
        cs.median_lsa_present_rate,
        cs.median_ads_present_rate,
        cs.median_aio_trigger_rate,
        cs.sample_size_metros,
        cs.sample_size_observations,
        CASE
            WHEN cs.sample_size_metros >= 20 THEN 'high'
            WHEN cs.sample_size_metros >= 8 THEN 'medium'
            WHEN cs.sample_size_metros >= 3 THEN 'low'
            ELSE 'insufficient'
        END AS confidence_label,
        now(),
        cs.computed_fact_window_start,
        cs.computed_fact_window_end
    FROM cell_stats cs
    ON CONFLICT (niche_normalized, population_class) DO UPDATE SET
        naics_code = EXCLUDED.naics_code,
        p25_total_volume_per_capita = EXCLUDED.p25_total_volume_per_capita,
        median_total_volume_per_capita = EXCLUDED.median_total_volume_per_capita,
        p75_total_volume_per_capita = EXCLUDED.p75_total_volume_per_capita,
        p25_avg_cpc = EXCLUDED.p25_avg_cpc,
        median_avg_cpc = EXCLUDED.median_avg_cpc,
        p75_avg_cpc = EXCLUDED.p75_avg_cpc,
        median_top3_review_count_min = EXCLUDED.median_top3_review_count_min,
        median_top3_review_velocity = EXCLUDED.median_top3_review_velocity,
        pct_with_local_pack = EXCLUDED.pct_with_local_pack,
        median_aggregator_count = EXCLUDED.median_aggregator_count,
        median_local_biz_count = EXCLUDED.median_local_biz_count,
        median_establishments_per_100k = EXCLUDED.median_establishments_per_100k,
        median_lsa_present_rate = EXCLUDED.median_lsa_present_rate,
        median_ads_present_rate = EXCLUDED.median_ads_present_rate,
        median_aio_trigger_rate = EXCLUDED.median_aio_trigger_rate,
        sample_size_metros = EXCLUDED.sample_size_metros,
        sample_size_observations = EXCLUDED.sample_size_observations,
        confidence_label = EXCLUDED.confidence_label,
        last_recomputed_at = now(),
        fact_window_start = EXCLUDED.fact_window_start,
        fact_window_end = EXCLUDED.fact_window_end;

    GET DIAGNOSTICS v_cells = ROW_COUNT;

    RETURN QUERY SELECT v_cells, v_start, v_end;
END;
$$;

REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM anon;
REVOKE ALL ON FUNCTION public.recompute_seo_benchmarks(INTEGER) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.recompute_seo_benchmarks(INTEGER) TO service_role;
