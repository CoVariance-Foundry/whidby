-- 006_authenticated_delete_reports.sql
-- Grant authenticated users DELETE access on the reports table.
--
-- Child tables (report_keywords, metro_signals, metro_scores) have
-- ON DELETE CASCADE foreign keys back to reports(id) — deleting a
-- report automatically removes all associated rows.  No additional
-- DELETE policies are needed on child tables.

CREATE POLICY "Authenticated users can delete reports"
    ON reports FOR DELETE
    TO authenticated
    USING (true);
