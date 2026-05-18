-- 019_explore_refresh_grants.sql
-- Forward-only Data API grants for environments that already applied
-- 015_explore_refresh_control.sql before explicit grants were added there.

DO $$
BEGIN
    IF to_regclass('public.explore_refresh_policies') IS NOT NULL THEN
        EXECUTE 'GRANT SELECT ON TABLE public.explore_refresh_policies TO authenticated';
        EXECUTE 'GRANT ALL ON TABLE public.explore_refresh_policies TO service_role';
    END IF;

    IF to_regclass('public.explore_refresh_targets') IS NOT NULL THEN
        EXECUTE 'GRANT SELECT ON TABLE public.explore_refresh_targets TO authenticated';
        EXECUTE 'GRANT ALL ON TABLE public.explore_refresh_targets TO service_role';
    END IF;

    IF to_regclass('public.explore_refresh_runs') IS NOT NULL THEN
        EXECUTE 'GRANT SELECT ON TABLE public.explore_refresh_runs TO authenticated';
        EXECUTE 'GRANT ALL ON TABLE public.explore_refresh_runs TO service_role';
    END IF;

    IF to_regclass('public.explore_refresh_run_items') IS NOT NULL THEN
        EXECUTE 'GRANT SELECT ON TABLE public.explore_refresh_run_items TO authenticated';
        EXECUTE 'GRANT ALL ON TABLE public.explore_refresh_run_items TO service_role';
    END IF;

    IF to_regclass('public.explore_report_snapshots') IS NOT NULL THEN
        EXECUTE 'GRANT SELECT ON TABLE public.explore_report_snapshots TO authenticated';
        EXECUTE 'GRANT ALL ON TABLE public.explore_report_snapshots TO service_role';
    END IF;

    IF to_regclass('public.explore_latest_target_scores') IS NOT NULL THEN
        EXECUTE 'GRANT SELECT ON TABLE public.explore_latest_target_scores TO authenticated';
        EXECUTE 'GRANT SELECT ON TABLE public.explore_latest_target_scores TO service_role';
    END IF;

    IF to_regclass('public.explore_target_trends') IS NOT NULL THEN
        EXECUTE 'GRANT SELECT ON TABLE public.explore_target_trends TO authenticated';
        EXECUTE 'GRANT SELECT ON TABLE public.explore_target_trends TO service_role';
    END IF;
END $$;
