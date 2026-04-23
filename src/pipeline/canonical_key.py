"""Canonical key resolution for knowledge base entities.

Produces deterministic (niche, geo) identity keys used to match incoming
scoring requests against existing KB entities and snapshots.  The
normalization is intentionally aggressive so that near-duplicate queries
("Roofing" vs "roofing near me", "Phoenix, AZ" vs "Phoenix") collapse
to the same entity when they would produce materially identical scoring
evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass


_STRIP_SUFFIXES = re.compile(
    r"\b(near me|services?|company|companies|contractors?|pros?|experts?)\b",
    re.IGNORECASE,
)
_MULTI_SPACE = re.compile(r"\s+")


def normalize_niche(raw: str) -> str:
    """Lowercase, strip trailing service-type suffixes, collapse whitespace."""
    text = raw.strip().lower()
    text = _STRIP_SUFFIXES.sub("", text)
    text = _MULTI_SPACE.sub(" ", text).strip()
    return text


def normalize_geo(city: str, state: str | None = None) -> str:
    """Produce a deterministic geo key from city + optional state."""
    city_clean = city.strip().lower()
    city_clean = _MULTI_SPACE.sub(" ", city_clean).strip()

    if "," in city_clean:
        parts = [p.strip() for p in city_clean.split(",", 1)]
        city_clean = parts[0]
        if not state and len(parts) > 1 and parts[1]:
            state = parts[1]

    state_clean = (state or "").strip().upper()
    if city_clean and state_clean:
        return f"{city_clean}, {state_clean}"
    return city_clean or state_clean


@dataclass(frozen=True)
class CanonicalKey:
    """Immutable identity for a niche+geo KB entity."""

    niche_normalized: str
    geo_normalized: str
    geo_scope: str
    place_id: str | None
    dataforseo_location_code: int | None

    def input_hash(self, strategy_profile: str = "balanced") -> str:
        """Deterministic hash of the inputs that affect scoring output."""
        payload = {
            "niche": self.niche_normalized,
            "geo": self.geo_normalized,
            "geo_scope": self.geo_scope,
            "strategy_profile": strategy_profile,
        }
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()


def resolve_canonical_key(
    *,
    niche: str,
    city: str,
    state: str | None = None,
    place_id: str | None = None,
    dataforseo_location_code: int | None = None,
    geo_scope: str = "city",
) -> CanonicalKey:
    """Build a canonical key from user-facing request parameters."""
    return CanonicalKey(
        niche_normalized=normalize_niche(niche),
        geo_normalized=normalize_geo(city, state),
        geo_scope=geo_scope,
        place_id=place_id.strip() if place_id else None,
        dataforseo_location_code=dataforseo_location_code,
    )
