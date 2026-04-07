"""Deterministic query hash for observation store cache keys.

Produces a SHA-256 hex digest from an endpoint path and its parameters,
normalizing key order and stripping non-semantic fields so the same
logical request always maps to the same hash.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

EXCLUDED_KEYS: frozenset[str] = frozenset({"tag", "postback_url", "pingback_url"})


def compute_query_hash(endpoint: str, params: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 hex digest for *endpoint* + *params*.

    Args:
        endpoint: DataForSEO endpoint path (e.g. ``serp/google/organic/task_post``).
        params: Request parameters dict.  Keys in :data:`EXCLUDED_KEYS` and
            ``None``-valued entries are stripped before hashing.

    Returns:
        64-character lowercase hex string.
    """
    clean_params = {
        k: v
        for k, v in sorted(params.items())
        if k not in EXCLUDED_KEYS and v is not None
    }
    canonical = json.dumps(
        {"endpoint": endpoint, "params": clean_params},
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
