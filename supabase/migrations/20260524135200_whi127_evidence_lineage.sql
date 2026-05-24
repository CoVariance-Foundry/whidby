-- 20260524135200_whi127_evidence_lineage.sql
--
-- WHI-127: persist local-place identifiers and raw SEO evidence lineage.
-- Adds nullable/backfillable columns and a service-role-only raw evidence layer.

CREATE TABLE IF NOT EXISTS public.seo_evidence_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL DEFAULT 'dataforseo',
    endpoint_path TEXT NOT NULL,
    evidence_family TEXT NOT NULL
        CONSTRAINT seo_evidence_artifacts_family_check
        CHECK (
            evidence_family IN (
                'serp',
                'maps',
                'reviews',
                'backlinks',
                'lighthouse',
                'keyword_volume',
                'keyword_overview'
            )
        ),
    normalized_request_params JSONB NOT NULL DEFAULT '{}'::jsonb
        CONSTRAINT seo_evidence_artifacts_request_params_object_check
        CHECK (jsonb_typeof(normalized_request_params) = 'object'),
    request_hash TEXT NOT NULL,
    response_hash TEXT,
    response_storage_uri TEXT,
    response_payload JSONB,
    cache_status TEXT NOT NULL DEFAULT 'unknown'
        CONSTRAINT seo_evidence_artifacts_cache_status_check
        CHECK (cache_status IN ('hit', 'miss', 'bypass', 'replay', 'unknown')),
    cost_usd NUMERIC(10,4) NOT NULL DEFAULT 0 CHECK (cost_usd >= 0),
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_window_start TIMESTAMPTZ,
    source_window_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, endpoint_path, request_hash)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'seo_evidence_artifacts_family_check'
          AND conrelid = 'public.seo_evidence_artifacts'::regclass
    ) THEN
        ALTER TABLE public.seo_evidence_artifacts
            ADD CONSTRAINT seo_evidence_artifacts_family_check
            CHECK (
                evidence_family IN (
                    'serp',
                    'maps',
                    'reviews',
                    'backlinks',
                    'lighthouse',
                    'keyword_volume',
                    'keyword_overview'
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'seo_evidence_artifacts_request_params_object_check'
          AND conrelid = 'public.seo_evidence_artifacts'::regclass
    ) THEN
        ALTER TABLE public.seo_evidence_artifacts
            ADD CONSTRAINT seo_evidence_artifacts_request_params_object_check
            CHECK (jsonb_typeof(normalized_request_params) = 'object');
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'seo_evidence_artifacts_cache_status_check'
          AND conrelid = 'public.seo_evidence_artifacts'::regclass
    ) THEN
        ALTER TABLE public.seo_evidence_artifacts
            ADD CONSTRAINT seo_evidence_artifacts_cache_status_check
            CHECK (cache_status IN ('hit', 'miss', 'bypass', 'replay', 'unknown'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'seo_evidence_artifacts_cost_usd_check'
          AND conrelid = 'public.seo_evidence_artifacts'::regclass
    ) THEN
        ALTER TABLE public.seo_evidence_artifacts
            ADD CONSTRAINT seo_evidence_artifacts_cost_usd_check
            CHECK (cost_usd >= 0);
    END IF;
END $$;

ALTER TABLE public.local_pack_listing_facts
    ADD COLUMN IF NOT EXISTS cid TEXT,
    ADD COLUMN IF NOT EXISTS place_id TEXT,
    ADD COLUMN IF NOT EXISTS source_query TEXT,
    ADD COLUMN IF NOT EXISTS dataforseo_location_code INTEGER,
    ADD COLUMN IF NOT EXISTS result_type TEXT,
    ADD COLUMN IF NOT EXISTS listing_url TEXT,
    ADD COLUMN IF NOT EXISTS domain TEXT,
    ADD COLUMN IF NOT EXISTS review_retrieval_mode TEXT,
    ADD COLUMN IF NOT EXISTS review_window_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS review_window_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS upstream_result_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS evidence_artifact_id UUID
        REFERENCES public.seo_evidence_artifacts(id) ON DELETE SET NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'local_pack_listing_facts_review_retrieval_mode_check'
          AND conrelid = 'public.local_pack_listing_facts'::regclass
    ) THEN
        ALTER TABLE public.local_pack_listing_facts
            ADD CONSTRAINT local_pack_listing_facts_review_retrieval_mode_check
            CHECK (
                review_retrieval_mode IS NULL
                OR review_retrieval_mode IN (
                    'cid',
                    'place_id',
                    'keyword',
                    'title',
                    'unknown'
                )
            );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_local_pack_listing_facts_cid
    ON public.local_pack_listing_facts(cid)
    WHERE cid IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_local_pack_listing_facts_place_id
    ON public.local_pack_listing_facts(place_id)
    WHERE place_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_seo_evidence_artifacts_family_collected
    ON public.seo_evidence_artifacts(evidence_family, collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_seo_evidence_artifacts_endpoint_request
    ON public.seo_evidence_artifacts(provider, endpoint_path, request_hash);

ALTER TABLE public.seo_evidence_artifacts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role manages SEO evidence artifacts"
    ON public.seo_evidence_artifacts;
CREATE POLICY "Service role manages SEO evidence artifacts"
    ON public.seo_evidence_artifacts FOR ALL TO service_role USING (true) WITH CHECK (true);

REVOKE ALL ON TABLE public.seo_evidence_artifacts FROM anon;
REVOKE ALL ON TABLE public.seo_evidence_artifacts FROM authenticated;
GRANT ALL ON TABLE public.seo_evidence_artifacts TO service_role;

COMMENT ON TABLE public.seo_evidence_artifacts IS
    'Raw benchmark and SEO provider evidence used to explain demand, SERP, Maps, review, backlink, Lighthouse, and keyword benchmark inputs.';
COMMENT ON COLUMN public.seo_evidence_artifacts.normalized_request_params IS
    'Canonical JSON object used with provider and endpoint_path to derive request_hash.';
COMMENT ON COLUMN public.seo_evidence_artifacts.response_hash IS
    'Hash of the raw response payload when payload or external storage is available.';
COMMENT ON COLUMN public.seo_evidence_artifacts.response_storage_uri IS
    'External storage pointer for raw responses that are too large or sensitive to inline.';
COMMENT ON COLUMN public.local_pack_listing_facts.cid IS
    'Stable Google local result CID for refreshes that should not depend on business-name matching.';
COMMENT ON COLUMN public.local_pack_listing_facts.place_id IS
    'Stable Google place identifier for local-pack and review enrichment refreshes.';
COMMENT ON COLUMN public.local_pack_listing_facts.evidence_artifact_id IS
    'Nullable link to the raw SEO evidence artifact that produced this local-pack row.';
