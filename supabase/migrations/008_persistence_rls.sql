-- 008_persistence_rls.sql
-- Row-Level Security for data persistence layer tables.
-- Same service_role-only pattern as 004_rls_policies.sql.

ALTER TABLE observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_metros ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_benchmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_niches ENABLE ROW LEVEL SECURITY;
ALTER TABLE anchor_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE anchor_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on observations"
    ON observations FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on canonical_metros"
    ON canonical_metros FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on canonical_benchmarks"
    ON canonical_benchmarks FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on canonical_niches"
    ON canonical_niches FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on anchor_configs"
    ON anchor_configs FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on anchor_runs"
    ON anchor_runs FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on signal_snapshots"
    ON signal_snapshots FOR ALL
    USING (auth.role() = 'service_role');
