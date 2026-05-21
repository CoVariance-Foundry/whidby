-- 021_v2_top5_fact_fields.sql
-- Add nullable top-5 organic fact fields for V2 benchmark inputs.

ALTER TABLE public.seo_facts
    ADD COLUMN IF NOT EXISTS avg_top5_da NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS avg_top5_lighthouse NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS top5_da_coverage NUMERIC(5,4),
    ADD COLUMN IF NOT EXISTS top5_lighthouse_coverage NUMERIC(5,4),
    ADD COLUMN IF NOT EXISTS top5_organic_data_confidence TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'seo_facts_top5_organic_confidence_check'
          AND conrelid = 'public.seo_facts'::regclass
    ) THEN
        ALTER TABLE public.seo_facts
            ADD CONSTRAINT seo_facts_top5_organic_confidence_check
            CHECK (
                top5_organic_data_confidence IS NULL
                OR top5_organic_data_confidence IN ('high', 'medium', 'low', 'missing')
            );
    END IF;
END $$;
