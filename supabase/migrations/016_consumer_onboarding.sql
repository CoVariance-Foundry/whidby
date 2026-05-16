-- 016_consumer_onboarding.sql
-- Durable consumer onboarding state for strategy routing, target capture,
-- resume behavior, and first-report handoff.

CREATE TABLE IF NOT EXISTS onboarding_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES user_profiles(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    intent TEXT CHECK (intent IN ('find_first', 'scale', 'coach_agency', 'researching')),
    focus TEXT,
    coach_or_agency TEXT CHECK (coach_or_agency IN ('coaching', 'agency', 'both')),
    referral_source TEXT,
    recommended_strategy_id TEXT,
    available_strategy_ids TEXT[] NOT NULL DEFAULT '{}',
    next_route TEXT,
    status TEXT NOT NULL DEFAULT 'profile_started' CHECK (
        status IN (
            'profile_started',
            'profile_completed',
            'strategy_recommended',
            'target_selected',
            'report_queued',
            'cached_route_selected',
            'upgrade_required',
            'report_ready'
        )
    ),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_onboarding_profiles_account
    ON onboarding_profiles (account_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS onboarding_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    onboarding_profile_id UUID NOT NULL REFERENCES onboarding_profiles(id) ON DELETE CASCADE,
    strategy_id TEXT NOT NULL,
    niche_keyword TEXT NOT NULL CHECK (length(trim(niche_keyword)) > 0),
    service_category_id TEXT,
    geo_scope TEXT NOT NULL CHECK (geo_scope IN ('city', 'state', 'region', 'nationwide')),
    city TEXT,
    state TEXT,
    cbsa_code TEXT REFERENCES metros(cbsa_code),
    place_id TEXT,
    dataforseo_location_code INTEGER,
    resolved_label TEXT,
    metadata_source TEXT CHECK (
        metadata_source IN ('typed', 'mapbox_selected', 'recent_history', 'fallback_cbsa')
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (onboarding_profile_id, strategy_id)
);

CREATE INDEX IF NOT EXISTS idx_onboarding_targets_profile
    ON onboarding_targets (onboarding_profile_id, updated_at DESC);

DROP TRIGGER IF EXISTS onboarding_profiles_set_updated_at ON onboarding_profiles;
CREATE TRIGGER onboarding_profiles_set_updated_at
    BEFORE UPDATE ON onboarding_profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS onboarding_targets_set_updated_at ON onboarding_targets;
CREATE TRIGGER onboarding_targets_set_updated_at
    BEFORE UPDATE ON onboarding_targets
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE onboarding_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE onboarding_targets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Account members can read onboarding profiles"
    ON onboarding_profiles;
CREATE POLICY "Account members can read onboarding profiles"
    ON onboarding_profiles FOR SELECT
    TO authenticated
    USING (public.is_account_member(account_id));

DROP POLICY IF EXISTS "Users can update own onboarding profile"
    ON onboarding_profiles;
CREATE POLICY "Users can update own onboarding profile"
    ON onboarding_profiles FOR UPDATE
    TO authenticated
    USING (user_id = (SELECT auth.uid()) AND public.is_account_member(account_id))
    WITH CHECK (user_id = (SELECT auth.uid()) AND public.is_account_member(account_id));

DROP POLICY IF EXISTS "Users can insert own onboarding profile"
    ON onboarding_profiles;
CREATE POLICY "Users can insert own onboarding profile"
    ON onboarding_profiles FOR INSERT
    TO authenticated
    WITH CHECK (user_id = (SELECT auth.uid()) AND public.is_account_member(account_id));

DROP POLICY IF EXISTS "Account members can read onboarding targets"
    ON onboarding_targets;
CREATE POLICY "Account members can read onboarding targets"
    ON onboarding_targets FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM onboarding_profiles op
            WHERE op.id = onboarding_targets.onboarding_profile_id
              AND public.is_account_member(op.account_id)
        )
    );

DROP POLICY IF EXISTS "Users can upsert own onboarding targets"
    ON onboarding_targets;
CREATE POLICY "Users can upsert own onboarding targets"
    ON onboarding_targets FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM onboarding_profiles op
            WHERE op.id = onboarding_targets.onboarding_profile_id
              AND op.user_id = (SELECT auth.uid())
              AND public.is_account_member(op.account_id)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM onboarding_profiles op
            WHERE op.id = onboarding_targets.onboarding_profile_id
              AND op.user_id = (SELECT auth.uid())
              AND public.is_account_member(op.account_id)
        )
    );

DROP POLICY IF EXISTS "Service role full access on onboarding_profiles"
    ON onboarding_profiles;
CREATE POLICY "Service role full access on onboarding_profiles"
    ON onboarding_profiles FOR ALL
    USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role full access on onboarding_targets"
    ON onboarding_targets;
CREATE POLICY "Service role full access on onboarding_targets"
    ON onboarding_targets FOR ALL
    USING (auth.role() = 'service_role');
