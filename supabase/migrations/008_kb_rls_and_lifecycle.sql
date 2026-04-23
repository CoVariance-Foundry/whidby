-- 008_kb_rls_and_lifecycle.sql
-- RLS policies for KB tables and tightened delete governance.
--
-- KB tables are service_role-only for writes.
-- Authenticated users get SELECT on snapshot/entity tables for UI reads.
-- Reports deletion is narrowed: soft-archive via archived_at column.

-- Enable RLS on all new KB tables
ALTER TABLE kb_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_evidence_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_response_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback_events ENABLE ROW LEVEL SECURITY;

-- Service-role full access
CREATE POLICY "Service role full access on kb_entities"
    ON kb_entities FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on kb_snapshots"
    ON kb_snapshots FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on kb_evidence_artifacts"
    ON kb_evidence_artifacts FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on api_response_cache"
    ON api_response_cache FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on feedback_events"
    ON feedback_events FOR ALL
    USING (auth.role() = 'service_role');

-- Authenticated users can read KB entities and current snapshots
CREATE POLICY "Authenticated users can read kb_entities"
    ON kb_entities FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can read kb_snapshots"
    ON kb_snapshots FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can read feedback_events"
    ON feedback_events FOR SELECT
    TO authenticated
    USING (true);

-- Add archived_at column to reports for soft-delete governance
ALTER TABLE reports ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS entity_id UUID REFERENCES kb_entities(id) ON DELETE SET NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS snapshot_id UUID REFERENCES kb_snapshots(id) ON DELETE SET NULL;

CREATE INDEX idx_reports_entity ON reports (entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_reports_snapshot ON reports (snapshot_id) WHERE snapshot_id IS NOT NULL;
CREATE INDEX idx_reports_archived ON reports (archived_at) WHERE archived_at IS NOT NULL;
