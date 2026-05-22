-- WHI-9 Competitor Intel schema, multi-unit quota RPCs, and read-model grants.

CREATE TABLE IF NOT EXISTS public.organic_competitor_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cbsa_code TEXT NOT NULL REFERENCES public.metros(cbsa_code),
    niche_normalized TEXT NOT NULL,
    keyword TEXT NOT NULL,
    result_rank INTEGER NOT NULL CHECK (result_rank > 0),
    title TEXT,
    domain TEXT,
    url TEXT,
    result_type TEXT NOT NULL DEFAULT 'organic',
    domain_authority NUMERIC(6,2),
    backlinks_count INTEGER CHECK (backlinks_count IS NULL OR backlinks_count >= 0),
    referring_domains_count INTEGER CHECK (
        referring_domains_count IS NULL OR referring_domains_count >= 0
    ),
    lighthouse_score NUMERIC(5,2),
    has_localbusiness_schema BOOLEAN,
    schema_types TEXT[] NOT NULL DEFAULT '{}'::text[],
    title_keyword_match BOOLEAN,
    is_aggregator BOOLEAN NOT NULL DEFAULT false,
    is_local_business BOOLEAN NOT NULL DEFAULT false,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    source TEXT NOT NULL DEFAULT 'dataforseo',
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cbsa_code, niche_normalized, keyword, result_rank, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_organic_competitor_facts_lookup
    ON public.organic_competitor_facts(
        cbsa_code,
        niche_normalized,
        keyword,
        snapshot_date DESC
    );

CREATE INDEX IF NOT EXISTS idx_organic_competitor_facts_report
    ON public.organic_competitor_facts(report_id)
    WHERE report_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.competitor_intel_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES public.accounts(id) ON DELETE SET NULL,
    created_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    report_id UUID REFERENCES public.reports(id) ON DELETE SET NULL,
    cbsa_code TEXT REFERENCES public.metros(cbsa_code),
    niche_normalized TEXT,
    service TEXT,
    keyword TEXT,
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    scan_cost_usd NUMERIC(10,4) NOT NULL DEFAULT 0 CHECK (scan_cost_usd >= 0),
    quota_consumed INTEGER NOT NULL DEFAULT 0 CHECK (quota_consumed >= 0),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (
        status IN ('queued', 'running', 'succeeded', 'partial_failed', 'failed', 'canceled')
    ),
    result_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_competitor_intel_runs_account_created
    ON public.competitor_intel_runs(account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_competitor_intel_runs_report
    ON public.competitor_intel_runs(report_id)
    WHERE report_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_competitor_intel_runs_status
    ON public.competitor_intel_runs(status, created_at DESC);

ALTER TABLE public.organic_competitor_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.competitor_intel_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can read organic competitor facts"
    ON public.organic_competitor_facts;

DROP POLICY IF EXISTS "Service role manages organic competitor facts"
    ON public.organic_competitor_facts;
CREATE POLICY "Service role manages organic competitor facts"
    ON public.organic_competitor_facts FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Authenticated users can read local pack listing facts"
    ON public.local_pack_listing_facts;
DROP POLICY IF EXISTS "Service role manages local pack listing facts"
    ON public.local_pack_listing_facts;
CREATE POLICY "Service role manages local pack listing facts"
    ON public.local_pack_listing_facts FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Account members can read competitor intel runs"
    ON public.competitor_intel_runs;
CREATE POLICY "Account members can read competitor intel runs"
    ON public.competitor_intel_runs FOR SELECT TO authenticated
    USING (
        account_id IS NOT NULL
        AND public.is_account_member(account_id)
    );

DROP POLICY IF EXISTS "Service role manages competitor intel runs"
    ON public.competitor_intel_runs;
CREATE POLICY "Service role manages competitor intel runs"
    ON public.competitor_intel_runs FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE OR REPLACE FUNCTION public.consume_usage_quota(
    p_account_id UUID,
    p_metric_key TEXT,
    p_units INT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_limit INT;
    v_period_start TIMESTAMPTZ;
    v_period_end TIMESTAMPTZ;
    v_consumed BOOLEAN;
BEGIN
    IF p_units IS NULL OR p_units <= 0 THEN
        RAISE EXCEPTION 'p_units must be a positive integer';
    END IF;

    IF p_metric_key IS NULL OR btrim(p_metric_key) = '' THEN
        RAISE EXCEPTION 'p_metric_key must be non-empty';
    END IF;

    IF NOT public.is_account_member(p_account_id) THEN
        RETURN false;
    END IF;

    SELECT
        pc.monthly_report_limit,
        COALESCE(s.current_period_start, date_trunc('month', now())),
        COALESCE(s.current_period_end, date_trunc('month', now()) + interval '1 month')
    INTO v_limit, v_period_start, v_period_end
    FROM subscriptions s
    JOIN plan_catalog pc ON pc.plan_key = CASE
        WHEN s.status IN ('active', 'trialing') THEN s.plan_key
        ELSE 'free'
    END
    WHERE s.account_id = p_account_id
    LIMIT 1;

    IF v_limit IS NULL OR v_limit <= 0 OR p_units > v_limit THEN
        RETURN false;
    END IF;

    WITH bumped AS (
        INSERT INTO usage_counters (
            account_id,
            metric_key,
            period_start,
            period_end,
            used_count
        )
        VALUES (
            p_account_id,
            p_metric_key,
            v_period_start,
            v_period_end,
            p_units
        )
        ON CONFLICT (account_id, metric_key, period_start, period_end)
        DO UPDATE SET
            used_count = usage_counters.used_count + p_units,
            updated_at = now()
        WHERE usage_counters.used_count + p_units <= v_limit
        RETURNING used_count
    )
    SELECT EXISTS (SELECT 1 FROM bumped) INTO v_consumed;

    RETURN v_consumed;
END;
$$;

CREATE OR REPLACE FUNCTION public.refund_usage_quota(
    p_account_id UUID,
    p_metric_key TEXT,
    p_units INT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_period_start TIMESTAMPTZ;
    v_period_end TIMESTAMPTZ;
BEGIN
    IF p_units IS NULL OR p_units <= 0 THEN
        RAISE EXCEPTION 'p_units must be a positive integer';
    END IF;

    IF p_metric_key IS NULL OR btrim(p_metric_key) = '' THEN
        RAISE EXCEPTION 'p_metric_key must be non-empty';
    END IF;

    IF auth.role() <> 'service_role' AND NOT public.is_account_member(p_account_id) THEN
        RETURN false;
    END IF;

    SELECT
        COALESCE(current_period_start, date_trunc('month', now())),
        COALESCE(current_period_end, date_trunc('month', now()) + interval '1 month')
    INTO v_period_start, v_period_end
    FROM subscriptions
    WHERE account_id = p_account_id
    LIMIT 1;

    UPDATE usage_counters
    SET used_count = GREATEST(used_count - p_units, 0),
        updated_at = now()
    WHERE account_id = p_account_id
      AND metric_key = p_metric_key
      AND period_start = v_period_start
      AND period_end = v_period_end
      AND used_count > 0;

    RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION public.consume_report_quota(p_account_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT public.consume_usage_quota(p_account_id, 'fresh_report', 1);
$$;

CREATE OR REPLACE FUNCTION public.refund_report_quota(p_account_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT public.refund_usage_quota(p_account_id, 'fresh_report', 1);
$$;

REVOKE ALL ON TABLE public.organic_competitor_facts FROM anon;
REVOKE ALL ON TABLE public.organic_competitor_facts FROM authenticated;
REVOKE ALL ON TABLE public.local_pack_listing_facts FROM anon;
REVOKE ALL ON TABLE public.local_pack_listing_facts FROM authenticated;
GRANT ALL ON TABLE public.organic_competitor_facts TO service_role;
GRANT SELECT ON TABLE public.competitor_intel_runs TO authenticated;
GRANT ALL ON TABLE public.competitor_intel_runs TO service_role;
GRANT ALL ON TABLE public.local_pack_listing_facts TO service_role;

GRANT EXECUTE ON FUNCTION public.consume_usage_quota(UUID, TEXT, INT) TO authenticated;
REVOKE EXECUTE ON FUNCTION public.refund_usage_quota(UUID, TEXT, INT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.refund_usage_quota(UUID, TEXT, INT) FROM anon;
REVOKE EXECUTE ON FUNCTION public.refund_usage_quota(UUID, TEXT, INT) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.refund_usage_quota(UUID, TEXT, INT) TO service_role;
GRANT EXECUTE ON FUNCTION public.consume_report_quota(UUID) TO authenticated;
REVOKE EXECUTE ON FUNCTION public.refund_report_quota(UUID) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.refund_report_quota(UUID) FROM anon;
REVOKE EXECUTE ON FUNCTION public.refund_report_quota(UUID) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.refund_report_quota(UUID) TO service_role;
