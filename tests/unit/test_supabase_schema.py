"""Unit tests for Supabase schema migrations (M2).

No live database — validates migration files exist, are non-empty,
and contain the expected table definitions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "supabase" / "migrations"


class TestMigrationFiles:
    def test_all_migration_files_exist(self):
        expected = [
            "001_core_schema.sql",
            "002_experiment_schema.sql",
            "003_shared_tables.sql",
            "004_rls_policies.sql",
        ]
        for name in expected:
            path = MIGRATIONS_DIR / name
            assert path.exists(), f"Missing migration: {name}"
            assert path.stat().st_size > 0, f"Empty migration: {name}"


class TestCoreSchema:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "001_core_schema.sql").read_text()

    def test_reports_table(self, sql: str):
        assert "CREATE TABLE" in sql
        assert "reports" in sql
        assert "niche_keyword" in sql

    def test_feedback_log_table(self, sql: str):
        assert "feedback_log" in sql
        assert "context" in sql
        assert "outcome" in sql

    def test_metro_scores_table(self, sql: str):
        assert "metro_scores" in sql
        assert "opportunity_score" in sql
        assert "serp_archetype" in sql


class TestExperimentSchema:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "002_experiment_schema.sql").read_text()

    def test_experiments_table(self, sql: str):
        assert "experiments" in sql
        assert "niche_keyword" in sql

    def test_rentability_signals_table(self, sql: str):
        assert "rentability_signals" in sql
        assert "UNIQUE(niche_keyword, cbsa_code)" in sql

    def test_outreach_events_table(self, sql: str):
        assert "outreach_events" in sql
        assert "event_type" in sql

    def test_foreign_keys(self, sql: str):
        assert "REFERENCES experiments(id)" in sql
        assert "REFERENCES experiment_businesses(id)" in sql


class TestSharedTables:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "003_shared_tables.sql").read_text()

    def test_api_usage_log(self, sql: str):
        assert "api_usage_log" in sql
        assert "endpoint" in sql
        assert "cost" in sql

    def test_metro_location_cache(self, sql: str):
        assert "metro_location_cache" in sql
        assert "dataforseo_location_codes" in sql

    def test_suppression_list(self, sql: str):
        assert "suppression_list" in sql


class TestRLSPolicies:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "004_rls_policies.sql").read_text()

    def test_rls_enabled_on_all_tables(self, sql: str):
        tables = [
            "reports", "report_keywords", "metro_signals", "metro_scores",
            "feedback_log", "experiments", "experiment_variants",
            "experiment_businesses", "outreach_events", "reply_classifications",
            "rentability_signals", "api_usage_log", "metro_location_cache",
            "suppression_list",
        ]
        for table in tables:
            assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql, (
                f"RLS not enabled for {table}"
            )

    def test_service_role_policies_exist(self, sql: str):
        assert "CREATE POLICY" in sql
        assert "service_role" in sql
