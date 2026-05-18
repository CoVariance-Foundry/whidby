-- 018_internal_user_entitlements.sql
-- Internal entitlement overrides and service-role admin account bootstrap.

-- ---------------------------------------------------------------------------
-- Internal entitlement overrides
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.internal_user_entitlements (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    fresh_report_quota_exempt BOOLEAN NOT NULL DEFAULT false,
    reason TEXT NOT NULL,
    granted_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_internal_user_entitlements_active_quota_exempt
    ON public.internal_user_entitlements (user_id, expires_at)
    WHERE fresh_report_quota_exempt = true;

ALTER TABLE public.internal_user_entitlements ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on internal_user_entitlements"
    ON public.internal_user_entitlements;

CREATE POLICY "Service role full access on internal_user_entitlements"
    ON public.internal_user_entitlements FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ---------------------------------------------------------------------------
-- Service-role account bootstrap
-- ---------------------------------------------------------------------------

DROP FUNCTION IF EXISTS public.ensure_account_for_user_admin(UUID, TEXT, TEXT, TEXT);

CREATE OR REPLACE FUNCTION public.ensure_account_for_user_admin(
    p_user_id UUID,
    p_email TEXT,
    p_member_role TEXT DEFAULT 'admin',
    p_plan_key TEXT DEFAULT 'free',
    p_overwrite_existing BOOLEAN DEFAULT false
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_account_id UUID;
BEGIN
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'user id required';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM (VALUES ('owner'), ('member'), ('admin')) AS allowed_roles(role)
        WHERE role IN ('owner', 'member', 'admin')
          AND role = p_member_role
    ) THEN
        RAISE EXCEPTION 'invalid member role: %', p_member_role;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM plan_catalog
        WHERE plan_key IN ('free', 'plus', 'pro')
          AND plan_key = p_plan_key
    ) THEN
        RAISE EXCEPTION 'invalid plan key: %', p_plan_key;
    END IF;

    PERFORM pg_advisory_xact_lock(
        ('x' || substr(replace(p_user_id::TEXT, '-', ''), 1, 8))::bit(32)::int,
        ('x' || substr(replace(p_user_id::TEXT, '-', ''), 9, 8))::bit(32)::int
    );

    INSERT INTO user_profiles (id, email)
    VALUES (p_user_id, NULLIF(btrim(p_email), ''))
    ON CONFLICT (id) DO UPDATE SET
        email = COALESCE(EXCLUDED.email, user_profiles.email),
        updated_at = now();

    SELECT account_id
    INTO v_account_id
    FROM account_memberships
    WHERE user_id = p_user_id
    ORDER BY created_at
    LIMIT 1;

    IF v_account_id IS NULL THEN
        INSERT INTO accounts (name)
        VALUES (COALESCE(NULLIF(btrim(p_email), ''), 'Widby account'))
        RETURNING id INTO v_account_id;
    END IF;

    INSERT INTO account_memberships (account_id, user_id, role)
    VALUES (v_account_id, p_user_id, p_member_role)
    ON CONFLICT (user_id) DO UPDATE SET
        account_id = EXCLUDED.account_id,
        role = EXCLUDED.role
    WHERE p_overwrite_existing;

    INSERT INTO subscriptions (account_id, plan_key, status)
    VALUES (v_account_id, p_plan_key, 'active')
    ON CONFLICT (account_id) DO UPDATE SET
        plan_key = EXCLUDED.plan_key,
        status = 'active',
        updated_at = now()
    WHERE p_overwrite_existing;

    RETURN v_account_id;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.ensure_account_for_user_admin(UUID, TEXT, TEXT, TEXT, BOOLEAN) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.ensure_account_for_user_admin(UUID, TEXT, TEXT, TEXT, BOOLEAN) FROM anon;
REVOKE EXECUTE ON FUNCTION public.ensure_account_for_user_admin(UUID, TEXT, TEXT, TEXT, BOOLEAN) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.ensure_account_for_user_admin(UUID, TEXT, TEXT, TEXT, BOOLEAN) TO service_role;

-- ---------------------------------------------------------------------------
-- Entitlement surface
-- ---------------------------------------------------------------------------

DROP FUNCTION IF EXISTS public.get_account_entitlement();

CREATE OR REPLACE FUNCTION public.get_account_entitlement()
RETURNS TABLE (
    account_id UUID,
    member_role TEXT,
    plan_key TEXT,
    monthly_report_limit INT,
    subscription_status TEXT,
    cancel_at_period_end BOOLEAN,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    fresh_report_quota_exempt BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_account_id UUID;
BEGIN
    v_account_id := public.ensure_account_for_current_user();

    RETURN QUERY
    SELECT
        am.account_id,
        am.role AS member_role,
        CASE
            WHEN s.status IN ('active', 'trialing') THEN s.plan_key
            ELSE 'free'
        END AS plan_key,
        pc.monthly_report_limit,
        COALESCE(s.status, 'active') AS subscription_status,
        COALESCE(s.cancel_at_period_end, false) AS cancel_at_period_end,
        COALESCE(s.current_period_start, date_trunc('month', now())) AS current_period_start,
        COALESCE(s.current_period_end, date_trunc('month', now()) + interval '1 month') AS current_period_end,
        COALESCE(iue.fresh_report_quota_exempt, false) AS fresh_report_quota_exempt
    FROM account_memberships am
    LEFT JOIN subscriptions s ON s.account_id = am.account_id
    LEFT JOIN public.internal_user_entitlements iue
        ON iue.user_id = am.user_id
       AND iue.fresh_report_quota_exempt = true
       AND (iue.expires_at IS NULL OR iue.expires_at > now())
    JOIN plan_catalog pc ON pc.plan_key = CASE
        WHEN s.status IN ('active', 'trialing') THEN s.plan_key
        ELSE 'free'
    END
    WHERE am.account_id = v_account_id
      AND am.user_id = (SELECT auth.uid())
    LIMIT 1;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.get_account_entitlement() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.get_account_entitlement() FROM anon;
GRANT EXECUTE ON FUNCTION public.get_account_entitlement() TO authenticated;
