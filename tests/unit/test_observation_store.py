"""Unit tests for the ObservationStore class.

Tests use mocked Supabase client — no live database needed.
"""

from __future__ import annotations

import gzip
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.dataforseo.observation_store import ObservationStore

from tests.fixtures.observation_fixtures import (
    SAMPLE_API_RESPONSE_DATA,
    SAMPLE_ENDPOINT,
    SAMPLE_PARAMS,
    error_observation_row,
    expired_observation_row,
    fresh_observation_row,
    partial_observation_row,
)


def _mock_supabase(select_return=None):
    """Build a mock Supabase client with chained query builder."""
    sb = MagicMock()

    table_mock = MagicMock()
    sb.table.return_value = table_mock

    select_builder = MagicMock()
    table_mock.select.return_value = select_builder
    select_builder.eq.return_value = select_builder
    select_builder.gt.return_value = select_builder
    select_builder.order.return_value = select_builder
    select_builder.limit.return_value = select_builder

    if select_return is not None:
        select_builder.execute.return_value = MagicMock(data=select_return)
    else:
        select_builder.execute.return_value = MagicMock(data=[])

    insert_builder = MagicMock()
    table_mock.insert.return_value = insert_builder
    insert_builder.execute.return_value = MagicMock(data=[{"id": "new-obs-id"}])

    storage_mock = MagicMock()
    sb.storage.from_.return_value = storage_mock
    storage_mock.upload.return_value = None
    storage_mock.download.return_value = gzip.compress(
        json.dumps(SAMPLE_API_RESPONSE_DATA).encode()
    )

    return sb


class TestCheckCache:
    def test_returns_data_for_fresh_observation(self):
        row = fresh_observation_row(query_hash="hash1")
        sb = _mock_supabase(select_return=[row])
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        result = store.check_cache("hash1")

        assert result is not None
        assert result["hit"] is True
        assert result["observation_id"] == row["id"]

    def test_returns_none_for_no_observations(self):
        sb = _mock_supabase(select_return=[])
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        result = store.check_cache("nonexistent-hash")

        assert result is None

    def test_skips_error_observations(self):
        row = error_observation_row(query_hash="hash1")
        sb = _mock_supabase(select_return=[row])
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        result = store.check_cache("hash1")

        assert result is None

    def test_skips_partial_observations(self):
        row = partial_observation_row(query_hash="hash1")
        sb = _mock_supabase(select_return=[row])
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        result = store.check_cache("hash1")

        assert result is None

    def test_downloads_payload_from_storage_on_hit(self):
        row = fresh_observation_row(query_hash="hash1")
        sb = _mock_supabase(select_return=[row])
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        result = store.check_cache("hash1")

        assert result is not None
        assert result["payload"] == SAMPLE_API_RESPONSE_DATA
        sb.storage.from_.assert_called_with("observations")


class TestStore:
    def test_inserts_observation_row_and_uploads_payload(self):
        sb = _mock_supabase()
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        record = store.store(
            endpoint=SAMPLE_ENDPOINT,
            params=SAMPLE_PARAMS,
            query_hash="hash123",
            ttl_category="serp",
            data=SAMPLE_API_RESPONSE_DATA,
            cost_usd=0.0006,
            source="pipeline",
            run_id=None,
            queue_mode="standard",
        )

        assert record is not None
        sb.table.assert_called_with("observations")
        sb.storage.from_.assert_called_with("observations")

    def test_writes_partial_row_on_storage_failure(self):
        sb = _mock_supabase()
        sb.storage.from_.return_value.upload.side_effect = Exception("Storage unavailable")
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        record = store.store(
            endpoint=SAMPLE_ENDPOINT,
            params=SAMPLE_PARAMS,
            query_hash="hash123",
            ttl_category="serp",
            data=SAMPLE_API_RESPONSE_DATA,
            cost_usd=0.0006,
            source="pipeline",
            run_id=None,
            queue_mode="standard",
        )

        assert record is not None
        assert record["status"] == "partial"
        assert record["storage_path"] is None

    def test_storage_path_follows_convention(self):
        sb = _mock_supabase()
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        record = store.store(
            endpoint=SAMPLE_ENDPOINT,
            params=SAMPLE_PARAMS,
            query_hash="abcdef1234567890",
            ttl_category="serp",
            data=SAMPLE_API_RESPONSE_DATA,
            cost_usd=0.0006,
            source="pipeline",
            run_id=None,
            queue_mode="standard",
        )

        path = record["storage_path"]
        assert path.startswith("observations/serp/")
        assert "abcdef1234567890" in path
        assert path.endswith(".json.gz")

    def test_payload_is_gzipped_json(self):
        sb = _mock_supabase()
        uploaded_data = {}

        def capture_upload(path, data, file_options=None):
            uploaded_data["bytes"] = data

        sb.storage.from_.return_value.upload = capture_upload
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        store.store(
            endpoint=SAMPLE_ENDPOINT,
            params=SAMPLE_PARAMS,
            query_hash="hash123",
            ttl_category="serp",
            data=SAMPLE_API_RESPONSE_DATA,
            cost_usd=0.0006,
            source="pipeline",
            run_id=None,
            queue_mode="standard",
        )

        raw = gzip.decompress(uploaded_data["bytes"])
        parsed = json.loads(raw)
        assert parsed == SAMPLE_API_RESPONSE_DATA

    def test_expires_at_computed_from_ttl_category(self):
        sb = _mock_supabase()
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        record = store.store(
            endpoint=SAMPLE_ENDPOINT,
            params=SAMPLE_PARAMS,
            query_hash="hash123",
            ttl_category="keyword",
            data=SAMPLE_API_RESPONSE_DATA,
            cost_usd=0.05,
            source="pipeline",
            run_id=None,
            queue_mode="standard",
        )

        expires = datetime.fromisoformat(record["expires_at"])
        now = datetime.now(timezone.utc)
        assert expires > now + timedelta(days=29)
        assert expires < now + timedelta(days=31)


class TestDownloadPayload:
    def test_decompresses_gzipped_json(self):
        sb = _mock_supabase()
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        result = store.download_payload("observations/serp/2026/04/05/hash_id.json.gz")

        assert result == SAMPLE_API_RESPONSE_DATA

    def test_returns_none_on_download_failure(self):
        sb = _mock_supabase()
        sb.storage.from_.return_value.download.side_effect = Exception("Not found")
        store = ObservationStore(supabase_client=sb, bucket_name="observations")

        result = store.download_payload("observations/serp/2026/04/05/hash_id.json.gz")

        assert result is None
