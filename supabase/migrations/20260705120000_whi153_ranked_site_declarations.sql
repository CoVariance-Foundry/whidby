-- WHI-153 ranked-site declaration persistence.
-- Account-scoped state that unlocks Expand & Conquer when active and declared
-- or verified. Declarations are deactivated with active=false instead of delete.

CREATE TABLE IF NOT EXISTS public.ranked_site_declarations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES public.accounts(id) ON DELETE CASCADE,
    created_by_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    updated_by_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    site_name TEXT NOT NULL CHECK (length(trim(site_name)) > 0),
    site_url TEXT CHECK (site_url IS NULL OR length(trim(site_url)) > 0),
    site_domain TEXT NOT NULL CHECK (length(trim(site_domain)) > 0),
    city TEXT NOT NULL CHECK (length(trim(city)) > 0),
    state TEXT NOT NULL CHECK (length(trim(state)) >= 2),
    cbsa_code TEXT REFERENCES public.metros(cbsa_code),
    niche_keyword TEXT NOT NULL CHECK (length(trim(niche_keyword)) > 0),
    niche_normalized TEXT NOT NULL CHECK (length(trim(niche_normalized)) > 0),
    proof_state TEXT NOT NULL DEFAULT 'declared' CHECK (
        proof_state IN ('declared', 'verified', 'needs_review', 'rejected')
    ),
    active BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    declared_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_at TIMESTAMPTZ,
    deactivated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ranked_site_declarations_account_active
    ON public.ranked_site_declarations(account_id, active, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_ranked_site_declarations_unlock
    ON public.ranked_site_declarations(account_id, updated_at DESC)
    WHERE active = true AND proof_state IN ('declared', 'verified');

CREATE INDEX IF NOT EXISTS idx_ranked_site_declarations_domain
    ON public.ranked_site_declarations(site_domain);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ranked_site_declarations_active_target
    ON public.ranked_site_declarations(
        account_id,
        site_domain,
        niche_normalized,
        lower(city),
        upper(state),
        COALESCE(cbsa_code, '')
    )
    WHERE active = true;

DROP TRIGGER IF EXISTS ranked_site_declarations_set_updated_at
    ON public.ranked_site_declarations;
CREATE TRIGGER ranked_site_declarations_set_updated_at
    BEFORE UPDATE ON public.ranked_site_declarations
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.ranked_site_declarations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Account members can read ranked site declarations"
    ON public.ranked_site_declarations;
CREATE POLICY "Account members can read ranked site declarations"
    ON public.ranked_site_declarations FOR SELECT
    TO authenticated
    USING (public.is_account_member(account_id));

DROP POLICY IF EXISTS "Users can insert own ranked site declarations"
    ON public.ranked_site_declarations;
CREATE POLICY "Users can insert own ranked site declarations"
    ON public.ranked_site_declarations FOR INSERT
    TO authenticated
    WITH CHECK (
        created_by_user_id = (SELECT auth.uid())
        AND public.is_account_member(account_id)
    );

DROP POLICY IF EXISTS "Users can update own ranked site declarations"
    ON public.ranked_site_declarations;
CREATE POLICY "Users can update own ranked site declarations"
    ON public.ranked_site_declarations FOR UPDATE
    TO authenticated
    USING (
        created_by_user_id = (SELECT auth.uid())
        AND public.is_account_member(account_id)
    )
    WITH CHECK (
        created_by_user_id = (SELECT auth.uid())
        AND public.is_account_member(account_id)
    );

DROP POLICY IF EXISTS "Service role full access on ranked site declarations"
    ON public.ranked_site_declarations;
CREATE POLICY "Service role full access on ranked site declarations"
    ON public.ranked_site_declarations FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

REVOKE ALL ON TABLE public.ranked_site_declarations FROM anon;
GRANT SELECT, INSERT, UPDATE ON TABLE public.ranked_site_declarations TO authenticated;
GRANT ALL ON TABLE public.ranked_site_declarations TO service_role;
