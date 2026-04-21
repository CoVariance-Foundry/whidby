-- 005_authenticated_read_reports.sql
-- Grant authenticated users SELECT access on the report-facing tables.
--
-- Motivation: the consumer app's /reports and /reports/{id} pages read
-- via supabase-ssr using the publishable (anon) key against a logged-in
-- user's session. Without a policy for the `authenticated` role, RLS
-- (migration 004) blocks the SELECT and users see an empty list.
--
-- Writes still require service_role (populated by the Python scoring
-- engine via src/clients/supabase_persistence.py). Service_role policies
-- from migration 004 remain in place for FOR ALL — we only add FOR SELECT
-- for authenticated here.
--
-- Scope: only the tables the consumer UI needs to display a report list
-- and a report detail (reports, report_keywords, metro_signals,
-- metro_scores). Experiment tables (outreach, reply_classifications,
-- etc.) remain service_role only — they are admin-surface concerns.

CREATE POLICY "Authenticated users can read reports"
    ON reports FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can read report_keywords"
    ON report_keywords FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can read metro_signals"
    ON metro_signals FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can read metro_scores"
    ON metro_scores FOR SELECT
    TO authenticated
    USING (true);
