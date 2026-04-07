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
            "005_observation_store.sql",
            "006_canonical_reference.sql",
            "007_anchor_system.sql",
            "008_persistence_rls.sql",
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


class TestObservationStore:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "005_observation_store.sql").read_text()

    def test_observations_table(self, sql: str):
        assert "observations" in sql
        assert "query_hash" in sql
        assert "ttl_category" in sql
        assert "expires_at" in sql
        assert "storage_path" in sql
        assert "payload_purged" in sql

    def test_observations_indexes(self, sql: str):
        assert "idx_obs_hash_fresh" in sql
        assert "idx_obs_hash_time" in sql
        assert "idx_obs_source_time" in sql
        assert "idx_obs_expires" in sql

    def test_observations_check_constraints(self, sql: str):
        assert "'pipeline'" in sql
        assert "'anchor'" in sql
        assert "'manual'" in sql
        assert "'ok'" in sql
        assert "'error'" in sql
        assert "'partial'" in sql


class TestCanonicalReference:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "006_canonical_reference.sql").read_text()

    def test_canonical_metros_table(self, sql: str):
        assert "canonical_metros" in sql
        assert "metro_size_tier" in sql
        assert "population" in sql

    def test_canonical_benchmarks_table(self, sql: str):
        assert "canonical_benchmarks" in sql
        assert "metric_name" in sql
        assert "sample_size" in sql
        assert "valid_until" in sql
        assert "UNIQUE(niche_keyword, metro_size_tier, metric_name)" in sql

    def test_canonical_niches_table(self, sql: str):
        assert "canonical_niches" in sql
        assert "parent_vertical" in sql
        assert "modifier_patterns" in sql


class TestAnchorSystem:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "007_anchor_system.sql").read_text()

    def test_anchor_configs_table(self, sql: str):
        assert "anchor_configs" in sql
        assert "tracked_keywords" in sql
        assert "max_daily_cost_usd" in sql
        assert "UNIQUE(niche_keyword, cbsa_code)" in sql

    def test_anchor_runs_table(self, sql: str):
        assert "anchor_runs" in sql
        assert "REFERENCES anchor_configs(id)" in sql

    def test_signal_snapshots_table(self, sql: str):
        assert "signal_snapshots" in sql
        assert "snapshot_date" in sql
        assert "observation_ids" in sql
        assert "UNIQUE(anchor_config_id, snapshot_date)" in sql
        assert "idx_snapshots_niche_metro" in sql


class TestPersistenceRLS:
    @pytest.fixture
    def sql(self) -> str:
        return (MIGRATIONS_DIR / "008_persistence_rls.sql").read_text()

    def test_rls_enabled_on_all_persistence_tables(self, sql: str):
        tables = [
            "observations",
            "canonical_metros",
            "canonical_benchmarks",
            "canonical_niches",
            "anchor_configs",
            "anchor_runs",
            "signal_snapshots",
        ]
        for table in tables:
            assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql, (
                f"RLS not enabled for {table}"
            )

    def test_service_role_policies_exist(self, sql: str):
        assert sql.count("CREATE POLICY") == 7
        assert "service_role" in sql
