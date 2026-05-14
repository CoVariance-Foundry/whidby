-- 014_user_management_billing.sql
-- Consumer account management, tiered report quotas, Stripe billing state,
-- PostHog-safe rollout boundaries, and account-scoped report RLS.

-- ---------------------------------------------------------------------------
-- Plans and accounts
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS plan_catalog (
    plan_key TEXT PRIMARY KEY CHECK (plan_key IN ('free', 'plus', 'pro')),
    display_name TEXT NOT NULL,
    monthly_price_cents INT NOT NULL CHECK (monthly_price_cents >= 0),
    monthly_report_limit INT NOT NULL CHECK (monthly_report_limit >= 0),
    stripe_price_env TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO plan_catalog (
    plan_key,
    display_name,
    monthly_price_cents,
    monthly_report_limit,
    stripe_price_env
) VALUES
    ('free', 'Free', 0, 0, NULL),
    ('plus', 'Plus', 4900, 10, 'STRIPE_PLUS_PRICE_ID'),
    ('pro', 'Pro', 10000, 50, 'STRIPE_PRO_PRICE_ID')
ON CONFLICT (plan_key) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    monthly_price_cents = EXCLUDED.monthly_price_cents,
    monthly_report_limit = EXCLUDED.monthly_report_limit,
    stripe_price_env = EXCLUDED.stripe_price_env,
    updated_at = now();

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS account_memberships (
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'owner' CHECK (role IN ('owner', 'member', 'admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_account_memberships_user
    ON account_memberships (user_id);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,
    plan_key TEXT NOT NULL REFERENCES plan_catalog(plan_key) DEFAULT 'free',
    status TEXT NOT NULL DEFAULT 'active',
    stripe_subscription_id TEXT UNIQUE,
    stripe_price_id TEXT,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_account
    ON subscriptions (account_id);

CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_subscription
    ON subscriptions (stripe_subscription_id)
    WHERE stripe_subscription_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS billing_customers (
    account_id UUID PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    stripe_customer_id TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usage_counters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    metric_key TEXT NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    used_count INT NOT NULL DEFAULT 0 CHECK (used_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (account_id, metric_key, period_start, period_end)
);

CREATE INDEX IF NOT EXISTS idx_usage_counters_account_metric
    ON usage_counters (account_id, metric_key, period_start DESC);

-- ---------------------------------------------------------------------------
-- Report ownership and shared cached report visibility
-- ---------------------------------------------------------------------------

ALTER TABLE reports
    ADD COLUMN IF NOT EXISTS owner_account_id UUID REFERENCES accounts(id) ON DELETE SET NULL;

ALTER TABLE reports
    ADD COLUMN IF NOT EXISTS created_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

ALTER TABLE reports
    ADD COLUMN IF NOT EXISTS access_scope TEXT NOT NULL DEFAULT 'cached';

UPDATE reports
SET access_scope = 'cached'
WHERE owner_account_id IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'reports_access_scope_check'
          AND conrelid = 'reports'::regclass
    ) THEN
        ALTER TABLE reports
            ADD CONSTRAINT reports_access_scope_check
            CHECK (access_scope IN ('cached', 'account'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'reports_scope_owner_consistency'
          AND conrelid = 'reports'::regclass
    ) THEN
        ALTER TABLE reports
            ADD CONSTRAINT reports_scope_owner_consistency
            CHECK (
                (access_scope = 'cached' AND owner_account_id IS NULL)
                OR (access_scope = 'account' AND owner_account_id IS NOT NULL)
            ) NOT VALID;

        ALTER TABLE reports VALIDATE CONSTRAINT reports_scope_owner_consistency;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_reports_owner_account
    ON reports (owner_account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reports_access_scope
    ON reports (access_scope, created_at DESC);

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.is_account_member(p_account_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM account_memberships
        WHERE account_id = p_account_id
          AND user_id = (SELECT auth.uid())
    );
$$;

CREATE OR REPLACE FUNCTION public.handle_new_user_account()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_account_id UUID;
    v_email TEXT;
BEGIN
    v_email := NEW.email;

    INSERT INTO user_profiles (id, email)
    VALUES (NEW.id, v_email)
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        updated_at = now();

    INSERT INTO accounts (name)
    VALUES (COALESCE(v_email, 'Widby account'))
    RETURNING id INTO v_account_id;

    INSERT INTO account_memberships (account_id, user_id, role)
    VALUES (v_account_id, NEW.id, 'owner')
    ON CONFLICT DO NOTHING;

    INSERT INTO subscriptions (account_id, plan_key, status)
    VALUES (v_account_id, 'free', 'active')
    ON CONFLICT (account_id) DO NOTHING;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created_account ON auth.users;
CREATE TRIGGER on_auth_user_created_account
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_account();

CREATE OR REPLACE FUNCTION public.ensure_account_for_current_user()
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_email TEXT;
    v_account_id UUID;
BEGIN
    v_user_id := (SELECT auth.uid());
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'authenticated user required';
    END IF;

    SELECT account_id
    INTO v_account_id
    FROM account_memberships
    WHERE user_id = v_user_id
    ORDER BY created_at
    LIMIT 1;

    IF v_account_id IS NOT NULL THEN
        RETURN v_account_id;
    END IF;

    SELECT email INTO v_email
    FROM auth.users
    WHERE id = v_user_id;

    INSERT INTO user_profiles (id, email)
    VALUES (v_user_id, v_email)
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        updated_at = now();

    INSERT INTO accounts (name)
    VALUES (COALESCE(v_email, 'Widby account'))
    RETURNING id INTO v_account_id;

    INSERT INTO account_memberships (account_id, user_id, role)
    VALUES (v_account_id, v_user_id, 'owner');

    INSERT INTO subscriptions (account_id, plan_key, status)
    VALUES (v_account_id, 'free', 'active')
    ON CONFLICT (account_id) DO NOTHING;

    RETURN v_account_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.get_account_entitlement()
RETURNS TABLE (
    account_id UUID,
    member_role TEXT,
    plan_key TEXT,
    monthly_report_limit INT,
    subscription_status TEXT,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ
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
        COALESCE(s.current_period_start, date_trunc('month', now())) AS current_period_start,
        COALESCE(s.current_period_end, date_trunc('month', now()) + interval '1 month') AS current_period_end
    FROM account_memberships am
    LEFT JOIN subscriptions s ON s.account_id = am.account_id
    JOIN plan_catalog pc ON pc.plan_key = CASE
        WHEN s.status IN ('active', 'trialing') THEN s.plan_key
        ELSE 'free'
    END
    WHERE am.account_id = v_account_id
      AND am.user_id = (SELECT auth.uid())
    LIMIT 1;
END;
$$;

CREATE OR REPLACE FUNCTION public.consume_report_quota(p_account_id UUID)
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

    IF v_limit IS NULL OR v_limit <= 0 THEN
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
            'fresh_report',
            v_period_start,
            v_period_end,
            1
        )
        ON CONFLICT (account_id, metric_key, period_start, period_end)
        DO UPDATE SET
            used_count = usage_counters.used_count + 1,
            updated_at = now()
        WHERE usage_counters.used_count < v_limit
        RETURNING used_count
    )
    SELECT EXISTS (SELECT 1 FROM bumped) INTO v_consumed;

    RETURN v_consumed;
END;
$$;

CREATE OR REPLACE FUNCTION public.refund_report_quota(p_account_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_period_start TIMESTAMPTZ;
    v_period_end TIMESTAMPTZ;
BEGIN
    IF NOT public.is_account_member(p_account_id) THEN
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
    SET used_count = GREATEST(used_count - 1, 0),
        updated_at = now()
    WHERE account_id = p_account_id
      AND metric_key = 'fresh_report'
      AND period_start = v_period_start
      AND period_end = v_period_end
      AND used_count > 0;

    RETURN FOUND;
END;
$$;

GRANT EXECUTE ON FUNCTION public.ensure_account_for_current_user() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_account_entitlement() TO authenticated;
GRANT EXECUTE ON FUNCTION public.consume_report_quota(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.refund_report_quota(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_account_member(UUID) TO authenticated;

-- ---------------------------------------------------------------------------
-- RLS
-- ---------------------------------------------------------------------------

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE account_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_counters ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own profile"
    ON user_profiles FOR SELECT
    TO authenticated
    USING (id = (SELECT auth.uid()));

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    TO authenticated
    USING (id = (SELECT auth.uid()))
    WITH CHECK (id = (SELECT auth.uid()));

CREATE POLICY "Account members can read accounts"
    ON accounts FOR SELECT
    TO authenticated
    USING (public.is_account_member(id));

CREATE POLICY "Account members can read memberships"
    ON account_memberships FOR SELECT
    TO authenticated
    USING (public.is_account_member(account_id));

CREATE POLICY "Account members can read subscriptions"
    ON subscriptions FOR SELECT
    TO authenticated
    USING (public.is_account_member(account_id));

CREATE POLICY "Account members can read billing customers"
    ON billing_customers FOR SELECT
    TO authenticated
    USING (public.is_account_member(account_id));

CREATE POLICY "Account members can read usage counters"
    ON usage_counters FOR SELECT
    TO authenticated
    USING (public.is_account_member(account_id));

CREATE POLICY "Service role full access on user_profiles"
    ON user_profiles FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on accounts"
    ON accounts FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on account_memberships"
    ON account_memberships FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on subscriptions"
    ON subscriptions FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on billing_customers"
    ON billing_customers FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on usage_counters"
    ON usage_counters FOR ALL
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Authenticated users can read reports" ON reports;
DROP POLICY IF EXISTS "Authenticated users can read report_keywords" ON report_keywords;
DROP POLICY IF EXISTS "Authenticated users can read metro_signals" ON metro_signals;
DROP POLICY IF EXISTS "Authenticated users can read metro_scores" ON metro_scores;
DROP POLICY IF EXISTS "Authenticated users can delete reports" ON reports;

CREATE POLICY "Authenticated users can read visible reports"
    ON reports FOR SELECT
    TO authenticated
    USING (
        access_scope = 'cached'
        OR (
            owner_account_id IS NOT NULL
            AND public.is_account_member(owner_account_id)
        )
    );

CREATE POLICY "Account members can update own reports"
    ON reports FOR UPDATE
    TO authenticated
    USING (
        access_scope = 'account'
        AND owner_account_id IS NOT NULL
        AND public.is_account_member(owner_account_id)
    )
    WITH CHECK (
        access_scope = 'account'
        AND owner_account_id IS NOT NULL
        AND public.is_account_member(owner_account_id)
    );

CREATE POLICY "Account members can delete own reports"
    ON reports FOR DELETE
    TO authenticated
    USING (
        access_scope = 'account'
        AND owner_account_id IS NOT NULL
        AND public.is_account_member(owner_account_id)
    );

CREATE POLICY "Authenticated users can read visible report_keywords"
    ON report_keywords FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM reports r
            WHERE r.id = report_keywords.report_id
              AND (
                  r.access_scope = 'cached'
                  OR (
                      r.owner_account_id IS NOT NULL
                      AND public.is_account_member(r.owner_account_id)
                  )
              )
        )
    );

CREATE POLICY "Authenticated users can read visible metro_signals"
    ON metro_signals FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM reports r
            WHERE r.id = metro_signals.report_id
              AND (
                  r.access_scope = 'cached'
                  OR (
                      r.owner_account_id IS NOT NULL
                      AND public.is_account_member(r.owner_account_id)
                  )
              )
        )
    );

CREATE POLICY "Authenticated users can read visible metro_scores"
    ON metro_scores FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM reports r
            WHERE r.id = metro_scores.report_id
              AND (
                  r.access_scope = 'cached'
                  OR (
                      r.owner_account_id IS NOT NULL
                      AND public.is_account_member(r.owner_account_id)
                  )
              )
        )
    );
