-- 023_billing_operations_hardening.sql
-- Billing checkout idempotency, webhook ordering, and admin-visible issue logs.

CREATE TABLE IF NOT EXISTS billing_checkout_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    plan_key TEXT NOT NULL REFERENCES plan_catalog(plan_key) CHECK (plan_key IN ('plus', 'pro')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled', 'expired')),
    stripe_checkout_session_id TEXT UNIQUE,
    stripe_checkout_url TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_checkout_sessions_one_pending_account
    ON billing_checkout_sessions (account_id)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_billing_checkout_sessions_account_status
    ON billing_checkout_sessions (account_id, status, expires_at DESC);

CREATE TABLE IF NOT EXISTS billing_operation_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'error', 'warning', 'info')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    stripe_checkout_session_id TEXT,
    stripe_event_id TEXT,
    public_message TEXT NOT NULL,
    internal_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_billing_operation_events_status_severity_created
    ON billing_operation_events (status, severity, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_billing_operation_events_account_created
    ON billing_operation_events (account_id, created_at DESC)
    WHERE account_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_billing_operation_events_stripe_event
    ON billing_operation_events (stripe_event_id)
    WHERE stripe_event_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS billing_webhook_events (
    stripe_event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    stripe_created_at TIMESTAMPTZ NOT NULL,
    processing_status TEXT NOT NULL DEFAULT 'processing' CHECK (processing_status IN ('processing', 'processed', 'failed', 'ignored')),
    attempt_count INT NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    last_error TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_billing_webhook_events_status_created
    ON billing_webhook_events (processing_status, stripe_created_at DESC);

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS last_stripe_event_id TEXT;

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS last_stripe_event_created_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_subscriptions_last_stripe_event
    ON subscriptions (last_stripe_event_created_at DESC)
    WHERE last_stripe_event_created_at IS NOT NULL;

ALTER TABLE billing_checkout_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_operation_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_webhook_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on billing checkout sessions"
    ON billing_checkout_sessions FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role full access on billing operation events"
    ON billing_operation_events FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role full access on billing webhook events"
    ON billing_webhook_events FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE OR REPLACE FUNCTION public.is_internal_admin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM account_memberships
        WHERE user_id = (SELECT auth.uid())
          AND role = 'admin'
    );
$$;

REVOKE EXECUTE ON FUNCTION public.is_internal_admin() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_internal_admin() TO authenticated;

CREATE POLICY "Authenticated admins can read billing operation events"
    ON billing_operation_events FOR SELECT
    TO authenticated
    USING (public.is_internal_admin());

CREATE POLICY "Authenticated admins can resolve billing operation events"
    ON billing_operation_events FOR UPDATE
    TO authenticated
    USING (public.is_internal_admin())
    WITH CHECK (public.is_internal_admin());

CREATE OR REPLACE FUNCTION public.list_billing_operation_events(
    p_status TEXT DEFAULT 'open',
    p_severity TEXT DEFAULT NULL,
    p_limit INT DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    severity TEXT,
    status TEXT,
    event_type TEXT,
    source TEXT,
    account_id UUID,
    user_id UUID,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    stripe_checkout_session_id TEXT,
    stripe_event_id TEXT,
    public_message TEXT,
    internal_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF NOT public.is_internal_admin() THEN
        RAISE EXCEPTION 'billing_admin_required' USING ERRCODE = '42501';
    END IF;

    RETURN QUERY
    SELECT
        e.id,
        e.severity,
        e.status,
        e.event_type,
        e.source,
        e.account_id,
        e.user_id,
        e.stripe_customer_id,
        e.stripe_subscription_id,
        e.stripe_checkout_session_id,
        e.stripe_event_id,
        e.public_message,
        e.internal_message,
        e.metadata,
        e.created_at,
        e.updated_at,
        e.resolved_at,
        e.resolved_by
    FROM billing_operation_events e
    WHERE (p_status = 'all' OR e.status = COALESCE(NULLIF(p_status, ''), 'open'))
      AND (p_severity IS NULL OR p_severity = '' OR e.severity = p_severity)
    ORDER BY e.created_at DESC
    LIMIT LEAST(GREATEST(COALESCE(p_limit, 50), 1), 100);
END;
$$;

CREATE OR REPLACE FUNCTION public.resolve_billing_operation_event(
    p_event_id UUID
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF NOT public.is_internal_admin() THEN
        RAISE EXCEPTION 'billing_admin_required' USING ERRCODE = '42501';
    END IF;

    UPDATE billing_operation_events
    SET
        status = 'resolved',
        resolved_at = now(),
        resolved_by = (SELECT auth.uid()),
        updated_at = now()
    WHERE id = p_event_id;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.list_billing_operation_events(TEXT, TEXT, INT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.resolve_billing_operation_event(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.list_billing_operation_events(TEXT, TEXT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_billing_operation_event(UUID) TO authenticated;
