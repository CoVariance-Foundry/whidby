-- Derived Explore read model. Source tables remain canonical.

DROP MATERIALIZED VIEW IF EXISTS public.explore_market_cells;

CREATE MATERIALIZED VIEW public.explore_market_cells AS
WITH latest_cbp_year AS (
    SELECT max(year) AS year FROM public.census_cbp_establishments
),
prior_cbp_year AS (
    SELECT max(c.year) AS year
    FROM public.census_cbp_establishments c
    CROSS JOIN latest_cbp_year latest
    WHERE c.year < latest.year
),
service_weights AS (
    SELECT
        niche_normalized,
        max(niche_keyword) AS niche_keyword,
        naics_code,
        weight
    FROM public.niche_naics_mapping
    GROUP BY niche_normalized, naics_code, weight
),
weighted_cbp AS (
    SELECT
        c.cbsa_code,
        w.niche_normalized,
        c.year,
        sum(coalesce(c.est, 0) * w.weight)::numeric AS weighted_establishments
    FROM public.census_cbp_establishments c
    JOIN service_weights w ON w.naics_code = c.naics_code
    GROUP BY c.cbsa_code, w.niche_normalized, c.year
),
latest_metrics AS (
    SELECT
        m.cbsa_code,
        m.niche_normalized,
        m.weighted_establishments AS latest_weighted_establishments
    FROM weighted_cbp m
    JOIN latest_cbp_year y ON y.year = m.year
),
prior_metrics AS (
    SELECT
        m.cbsa_code,
        m.niche_normalized,
        m.weighted_establishments AS prior_weighted_establishments,
        y.year AS prior_year
    FROM weighted_cbp m
    JOIN prior_cbp_year y ON y.year = m.year
),
legacy_score_rows AS (
    SELECT
        ms.cbsa_code,
        regexp_replace(
            regexp_replace(
                lower(trim(r.niche_keyword)),
                '\s+(services?|company|contractors?)$',
                ''
            ),
            '\s+',
            '_',
            'g'
        ) AS niche_normalized,
        r.niche_keyword,
        ms.report_id,
        ms.opportunity_score,
        r.created_at,
        ms.serp_archetype,
        ms.ai_exposure,
        ms.difficulty_tier,
        ms.confidence_score,
        ms.ai_resilience_score
    FROM public.metro_scores ms
    JOIN public.reports r ON r.id = ms.report_id
),
latest_legacy_scores AS (
    SELECT DISTINCT ON (legacy.cbsa_code, legacy.niche_normalized)
        legacy.cbsa_code,
        legacy.niche_normalized,
        legacy.niche_keyword,
        legacy.report_id,
        legacy.opportunity_score AS presentation_score,
        'legacy'::text AS score_system,
        legacy.created_at AS latest_scored_at,
        legacy.serp_archetype,
        legacy.ai_exposure,
        legacy.difficulty_tier,
        legacy.confidence_score,
        legacy.ai_resilience_score
    FROM legacy_score_rows legacy
    ORDER BY legacy.cbsa_code, legacy.niche_normalized, legacy.created_at DESC
),
latest_v2_scores AS (
    SELECT DISTINCT ON (v2.cbsa_code, v2.niche_normalized)
        v2.cbsa_code,
        v2.niche_normalized,
        v2.niche_normalized AS niche_keyword,
        NULL::uuid AS report_id,
        greatest(
            coalesce(v2.demand_strength, 0) / 2,
            0
        )::integer AS presentation_score,
        'v2'::text AS score_system,
        v2.scored_at AS latest_scored_at,
        v2.benchmark_confidence,
        v2.demand_strength,
        v2.organic_difficulty,
        v2.local_difficulty,
        v2.monetization_signal,
        v2.ai_resilience
    FROM public.metro_score_v2 v2
    ORDER BY v2.cbsa_code, v2.niche_normalized, v2.scored_at DESC
),
score_union AS (
    SELECT
        coalesce(v2.cbsa_code, legacy.cbsa_code) AS cbsa_code,
        coalesce(v2.niche_normalized, legacy.niche_normalized) AS niche_normalized,
        coalesce(v2.niche_keyword, legacy.niche_keyword) AS niche_keyword,
        coalesce(v2.report_id, legacy.report_id) AS report_id,
        coalesce(v2.presentation_score, legacy.presentation_score) AS presentation_score,
        CASE WHEN v2.cbsa_code IS NOT NULL THEN 'v2' ELSE legacy.score_system END AS score_system,
        coalesce(v2.latest_scored_at, legacy.latest_scored_at) AS latest_scored_at,
        legacy.serp_archetype,
        legacy.ai_exposure,
        legacy.difficulty_tier,
        legacy.confidence_score,
        coalesce(v2.ai_resilience, legacy.ai_resilience_score) AS ai_resilience_score,
        v2.benchmark_confidence,
        v2.demand_strength,
        v2.organic_difficulty,
        v2.local_difficulty,
        v2.monetization_signal
    FROM latest_legacy_scores legacy
    FULL OUTER JOIN latest_v2_scores v2
      ON v2.cbsa_code = legacy.cbsa_code
     AND v2.niche_normalized = legacy.niche_normalized
),
refresh AS (
    SELECT DISTINCT ON (t.cbsa_code, t.niche_normalized)
        t.id AS refresh_target_id,
        t.cbsa_code,
        t.niche_normalized,
        t.next_refresh_at,
        t.latest_scored_at AS refresh_scored_at,
        COALESCE(p.cadence_days, 30) AS cadence_days
    FROM public.explore_refresh_targets t
    JOIN public.explore_refresh_policies p ON p.id = t.policy_id
    WHERE t.active IS TRUE
      AND p.enabled IS TRUE
    ORDER BY
        t.cbsa_code,
        t.niche_normalized,
        t.priority ASC,
        t.next_refresh_at ASC NULLS LAST,
        t.updated_at DESC,
        t.created_at DESC
)
SELECT
    metro.cbsa_code,
    metro.cbsa_name,
    metro.state,
    metro.population,
    metro.population_class,
    metro.median_household_income_usd,
    metro.owner_occupancy_rate,
    metro.median_age_years,
    score.niche_normalized,
    score.niche_keyword,
    score.report_id,
    score.presentation_score,
    score.score_system,
    score.latest_scored_at,
    latest.latest_weighted_establishments,
    prior.prior_weighted_establishments,
    CASE
        WHEN metro.population IS NULL OR metro.population <= 0 OR latest.latest_weighted_establishments IS NULL
        THEN NULL
        ELSE round((latest.latest_weighted_establishments / metro.population) * 1000, 10)
    END AS business_density_per_1k,
    CASE
        WHEN prior.prior_weighted_establishments IS NULL
          OR prior.prior_weighted_establishments <= 0
          OR latest.latest_weighted_establishments IS NULL
          OR prior.prior_year IS NULL
        THEN NULL
        ELSE round(
            power(
                latest.latest_weighted_establishments / prior.prior_weighted_establishments,
                1.0 / ((SELECT year FROM latest_cbp_year) - prior.prior_year)
            ) - 1,
            10
        )
    END AS establishment_growth_yoy,
    prior.prior_weighted_establishments IS NOT NULL AS growth_available,
    refresh.refresh_target_id,
    refresh.next_refresh_at,
    CASE
        WHEN score.latest_scored_at IS NULL THEN false
        ELSE score.latest_scored_at < now() - (COALESCE(refresh.cadence_days, 30) * interval '1 day')
    END AS stale,
    score.serp_archetype,
    score.ai_exposure,
    score.difficulty_tier,
    score.confidence_score,
    score.ai_resilience_score,
    score.benchmark_confidence,
    score.demand_strength,
    score.organic_difficulty,
    score.local_difficulty,
    score.monetization_signal
FROM public.metros metro
JOIN score_union score ON score.cbsa_code = metro.cbsa_code
LEFT JOIN latest_metrics latest
  ON latest.cbsa_code = score.cbsa_code
 AND latest.niche_normalized = score.niche_normalized
LEFT JOIN prior_metrics prior
  ON prior.cbsa_code = score.cbsa_code
 AND prior.niche_normalized = score.niche_normalized
LEFT JOIN refresh
  ON refresh.cbsa_code = score.cbsa_code
 AND refresh.niche_normalized = score.niche_normalized
WHERE metro.population IS NOT NULL;

CREATE UNIQUE INDEX idx_explore_market_cells_niche_cbsa
    ON public.explore_market_cells(niche_normalized, cbsa_code);
CREATE INDEX idx_explore_market_cells_cbsa
    ON public.explore_market_cells(cbsa_code);
CREATE INDEX idx_explore_market_cells_score
    ON public.explore_market_cells(presentation_score DESC NULLS LAST);
CREATE INDEX idx_explore_market_cells_scored_at
    ON public.explore_market_cells(latest_scored_at DESC NULLS LAST);

GRANT SELECT ON public.explore_market_cells TO authenticated;
GRANT SELECT ON public.explore_market_cells TO service_role;
