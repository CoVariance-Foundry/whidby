"""Backfill existing reports rows into kb_entities and kb_snapshots.

Run once after deploying migrations 007/008:

    python -m scripts.backfill_kb_entities

Reads all reports that lack an entity_id and creates canonical
KB entity + snapshot rows, then links them back.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _normalize_niche(raw: str) -> str:
    import re
    text = raw.strip().lower()
    text = re.sub(
        r"\b(near me|services?|company|companies|contractors?|pros?|experts?)\b",
        "", text, flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", text).strip()


def _normalize_geo(geo_target: str) -> str:
    from src.pipeline.canonical_key import normalize_geo
    return normalize_geo(geo_target)


def _input_hash(niche_norm: str, geo_norm: str, strategy: str) -> str:
    payload = json.dumps({
        "niche": niche_norm, "geo": geo_norm,
        "geo_scope": "city", "strategy_profile": strategy,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def main() -> None:
    try:
        from supabase import create_client
    except ImportError:
        logger.error("supabase-py not installed")
        sys.exit(1)

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    client = create_client(url, key)

    res = (
        client.table("reports")
        .select("id, niche_keyword, geo_scope, geo_target, strategy_profile, "
                "keyword_expansion, metros, meta, created_at, spec_version")
        .is_("entity_id", "null")
        .order("created_at", desc=False)
        .limit(500)
        .execute()
    )

    rows = res.data or []
    logger.info("Found %d reports without entity_id", len(rows))

    created_entities = 0
    created_snapshots = 0
    linked = 0

    for row in rows:
        niche_norm = _normalize_niche(row["niche_keyword"])
        geo_norm = _normalize_geo(row["geo_target"])
        geo_scope = row.get("geo_scope") or "city"
        strategy = row.get("strategy_profile") or "balanced"

        entity_row = {
            "niche_keyword_normalized": niche_norm,
            "geo_target_normalized": geo_norm,
            "geo_scope": geo_scope,
            "country_iso_code": "US",
        }

        entity_res = (
            client.table("kb_entities")
            .upsert(entity_row, on_conflict="niche_keyword_normalized,geo_target_normalized,geo_scope")
            .execute()
        )
        entity_id = entity_res.data[0]["id"]
        created_entities += 1

        ih = _input_hash(niche_norm, geo_norm, strategy)

        existing = (
            client.table("kb_snapshots")
            .select("id")
            .eq("entity_id", entity_id)
            .eq("is_current", True)
            .limit(1)
            .execute()
        )

        if existing.data:
            old_snap = existing.data[0]["id"]
            snap_id = str(uuid4())
            client.table("kb_snapshots").update({
                "is_current": False,
                "valid_to": datetime.now(UTC).isoformat(),
                "superseded_by": snap_id,
            }).eq("id", old_snap).execute()
        else:
            snap_id = str(uuid4())

        metro = row["metros"][0] if isinstance(row.get("metros"), list) and row["metros"] else {}
        version_res = (
            client.table("kb_snapshots")
            .select("version")
            .eq("entity_id", entity_id)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        next_version = (version_res.data[0]["version"] + 1) if version_res.data else 1

        snap_row: dict[str, Any] = {
            "id": snap_id,
            "entity_id": entity_id,
            "version": next_version,
            "valid_from": row["created_at"],
            "is_current": True,
            "input_hash": ih,
            "strategy_profile": strategy,
            "spec_version": row.get("spec_version", "1.1"),
            "keyword_expansion": row.get("keyword_expansion"),
            "signals": metro.get("signals"),
            "scores": metro.get("scores"),
            "classification": {
                "serp_archetype": metro.get("serp_archetype"),
                "ai_exposure": metro.get("ai_exposure"),
                "difficulty_tier": metro.get("difficulty_tier"),
            } if metro else None,
            "guidance": metro.get("guidance"),
            "meta": row.get("meta"),
            "report_id": row["id"],
        }

        client.table("kb_snapshots").insert(snap_row).execute()
        created_snapshots += 1

        client.table("reports").update({
            "entity_id": entity_id,
            "snapshot_id": snap_id,
        }).eq("id", row["id"]).execute()
        linked += 1

    logger.info(
        "Backfill complete: entities=%d snapshots=%d linked=%d",
        created_entities, created_snapshots, linked,
    )


if __name__ == "__main__":
    main()
