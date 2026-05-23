-- Metro DataForSEO readiness provenance.
--
-- `metros.dataforseo_location_codes` remains the canonical array consumed by
-- scoring. These nullable fields record how the current DFS code was matched
-- and verified so production enrichment can fail closed when provenance schema
-- is missing.

ALTER TABLE public.metros
  ADD COLUMN IF NOT EXISTS dataforseo_location_match_name TEXT,
  ADD COLUMN IF NOT EXISTS dataforseo_location_match_confidence TEXT,
  ADD COLUMN IF NOT EXISTS dataforseo_location_match_source TEXT,
  ADD COLUMN IF NOT EXISTS dataforseo_location_verified_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS dataforseo_location_review_reason TEXT;

ALTER TABLE public.metros
  DROP CONSTRAINT IF EXISTS metros_dfs_location_match_confidence_check;

ALTER TABLE public.metros
  ADD CONSTRAINT metros_dfs_location_match_confidence_check
  CHECK (
    dataforseo_location_match_confidence IS NULL
    OR dataforseo_location_match_confidence IN (
      'existing',
      'exact',
      'strong',
      'manual',
      'invalid',
      'unresolved'
    )
  );

CREATE INDEX IF NOT EXISTS idx_metros_dfs_verified_at
  ON public.metros(dataforseo_location_verified_at)
  WHERE dataforseo_location_verified_at IS NOT NULL;

COMMENT ON COLUMN public.metros.dataforseo_location_match_name IS
  'DataForSEO location_name used to verify or enrich dataforseo_location_codes.';
COMMENT ON COLUMN public.metros.dataforseo_location_match_confidence IS
  'DFS match provenance: existing, exact, strong, manual, invalid, or unresolved.';
COMMENT ON COLUMN public.metros.dataforseo_location_match_source IS
  'Tool or operator source that verified the DFS code, such as audit_metro_dfs_readiness or enrich_metro_dfs_codes.';
COMMENT ON COLUMN public.metros.dataforseo_location_verified_at IS
  'Timestamp when the DFS location code was last verified against the DataForSEO locations catalog.';
COMMENT ON COLUMN public.metros.dataforseo_location_review_reason IS
  'Short review note for manual, ambiguous, invalid, or unresolved DFS matches.';
