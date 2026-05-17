-- 016_strategy_discovery_system.sql
-- Strategy run lineage and strategy-specific evidence tables.

CREATE TABLE IF NOT EXISTS public.strategy_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES public.accounts(id) ON DELETE SET NULL,
    created_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    strategy_id TEXT NOT NULL CHECK (strategy_id IN (
        'easy_win', 'gbp_blitz', 'keyword_hijack', 'expand_conquer', 'cash_cow'
    )),
    mode TEXT NOT NULL DEFAULT 'cached' CHECK (mode IN ('cached', 'fresh')),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN (
        'queued', 'running', 'succeeded', 'partial_failed', 'failed', 'canceled'
    )),
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_count INTEGER NOT NULL DEFAULT 0 CHECK (result_count >= 0),
    quota_consumed INTEGER NOT NULL DEFAULT 0 CHECK (quota_consumed >= 0),
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_strategy_runs_account_created
    ON public.strategy_runs(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.strategy_run_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES public.strategy_runs(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL CHECK (rank > 0),
    strategy_id TEXT NOT NULL CHECK (strategy_id IN (
        'easy_win', 'gbp_blitz', 'keyword_hijack', 'expand_conquer', 'cash_cow'
    )),
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code),
    niche_normalized TEXT NOT NULL,
    niche_keyword TEXT NOT NULL,
    primary_keyword TEXT,
    report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    score NUMERIC(5,2) NOT NULL CHECK (score >= 0 AND score <= 100),
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, rank)
);

CREATE INDEX IF NOT EXISTS idx_strategy_run_items_run_rank
    ON public.strategy_run_items(run_id, rank);

CREATE TABLE IF NOT EXISTS public.local_pack_listing_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code),
    niche_normalized TEXT NOT NULL,
    keyword TEXT NOT NULL,
    listing_rank INTEGER NOT NULL CHECK (listing_rank > 0),
    business_name TEXT NOT NULL,
    exact_match_name BOOLEAN NOT NULL DEFAULT FALSE,
    review_count INTEGER,
    review_velocity_monthly NUMERIC(8,2),
    rating NUMERIC(3,2),
    gbp_completeness NUMERIC(5,4),
    photo_count INTEGER,
    has_recent_post BOOLEAN,
    categories TEXT[] NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'dataforseo',
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cbsa_code, niche_normalized, keyword, listing_rank, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_local_pack_facts_lookup
    ON public.local_pack_listing_facts(cbsa_code, niche_normalized, keyword, snapshot_date DESC);

CREATE TABLE IF NOT EXISTS public.metro_feature_vectors (
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code) ON DELETE CASCADE,
    feature_version TEXT NOT NULL DEFAULT 'strategy_v1',
    feature_vector JSONB NOT NULL,
    archetype TEXT,
    source_tables JSONB NOT NULL DEFAULT '[]'::jsonb,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (cbsa_code, feature_version)
);

CREATE TABLE IF NOT EXISTS public.strategy_score_cache (
    strategy_id TEXT NOT NULL CHECK (strategy_id IN (
        'easy_win', 'gbp_blitz', 'keyword_hijack', 'expand_conquer', 'cash_cow'
    )),
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code) ON DELETE CASCADE,
    niche_normalized TEXT NOT NULL,
    primary_keyword TEXT NOT NULL DEFAULT '',
    score NUMERIC(5,2) NOT NULL CHECK (score >= 0 AND score <= 100),
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (strategy_id, cbsa_code, niche_normalized, primary_keyword)
);

CREATE INDEX IF NOT EXISTS idx_strategy_score_cache_scored_at
    ON public.strategy_score_cache(strategy_id, scored_at DESC);

ALTER TABLE public.strategy_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategy_run_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.local_pack_listing_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.metro_feature_vectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategy_score_cache ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role manages strategy runs"
    ON public.strategy_runs;
CREATE POLICY "Service role manages strategy runs"
    ON public.strategy_runs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Account members can read strategy runs"
    ON public.strategy_runs;
CREATE POLICY "Account members can read strategy runs"
    ON public.strategy_runs FOR SELECT TO authenticated
    USING (
        account_id IS NOT NULL
        AND public.is_account_member(account_id)
    );

DROP POLICY IF EXISTS "Service role manages strategy run items"
    ON public.strategy_run_items;
CREATE POLICY "Service role manages strategy run items"
    ON public.strategy_run_items FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Account members can read strategy run items"
    ON public.strategy_run_items;
CREATE POLICY "Account members can read strategy run items"
    ON public.strategy_run_items FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM public.strategy_runs sr
            WHERE sr.id = strategy_run_items.run_id
              AND sr.account_id IS NOT NULL
              AND public.is_account_member(sr.account_id)
        )
    );

DROP POLICY IF EXISTS "Authenticated users can read local pack listing facts"
    ON public.local_pack_listing_facts;
CREATE POLICY "Authenticated users can read local pack listing facts"
    ON public.local_pack_listing_facts FOR SELECT TO authenticated
    USING (
        report_id IS NULL
        OR EXISTS (
            SELECT 1
            FROM public.reports r
            WHERE r.id = local_pack_listing_facts.report_id
              AND (
                  r.access_scope = 'cached'
                  OR (
                      r.owner_account_id IS NOT NULL
                      AND public.is_account_member(r.owner_account_id)
                  )
              )
        )
    );

DROP POLICY IF EXISTS "Authenticated users can read metro feature vectors"
    ON public.metro_feature_vectors;
CREATE POLICY "Authenticated users can read metro feature vectors"
    ON public.metro_feature_vectors FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Authenticated users can read strategy score cache"
    ON public.strategy_score_cache;
CREATE POLICY "Authenticated users can read strategy score cache"
    ON public.strategy_score_cache FOR SELECT TO authenticated
    USING (
        source_report_id IS NULL
        OR EXISTS (
            SELECT 1
            FROM public.reports r
            WHERE r.id = strategy_score_cache.source_report_id
              AND (
                  r.access_scope = 'cached'
                  OR (
                      r.owner_account_id IS NOT NULL
                      AND public.is_account_member(r.owner_account_id)
                  )
              )
        )
    );

DROP POLICY IF EXISTS "Service role manages local pack listing facts"
    ON public.local_pack_listing_facts;
CREATE POLICY "Service role manages local pack listing facts"
    ON public.local_pack_listing_facts FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role manages metro feature vectors"
    ON public.metro_feature_vectors;
CREATE POLICY "Service role manages metro feature vectors"
    ON public.metro_feature_vectors FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Service role manages strategy score cache"
    ON public.strategy_score_cache;
CREATE POLICY "Service role manages strategy score cache"
    ON public.strategy_score_cache FOR ALL TO service_role USING (true) WITH CHECK (true);
