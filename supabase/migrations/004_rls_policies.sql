-- 004_rls_policies.sql
-- Row-Level Security for internal-only access.
-- All tables require the service_role key — no anonymous/public access.

ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE metro_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE metro_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE outreach_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE reply_classifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE rentability_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE metro_location_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppression_list ENABLE ROW LEVEL SECURITY;

-- Service-role has full access (bypasses RLS by default in Supabase).
-- These policies grant access to authenticated users with the service_role.
-- For the internal eval dashboard, we'll use service_role key.

CREATE POLICY "Service role full access on reports"
    ON reports FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on report_keywords"
    ON report_keywords FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on metro_signals"
    ON metro_signals FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on metro_scores"
    ON metro_scores FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on feedback_log"
    ON feedback_log FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on experiments"
    ON experiments FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on experiment_variants"
    ON experiment_variants FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on experiment_businesses"
    ON experiment_businesses FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on outreach_events"
    ON outreach_events FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on reply_classifications"
    ON reply_classifications FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on rentability_signals"
    ON rentability_signals FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on api_usage_log"
    ON api_usage_log FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on metro_location_cache"
    ON metro_location_cache FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on suppression_list"
    ON suppression_list FOR ALL
    USING (auth.role() = 'service_role');
