"""Helpers for place autocomplete and DataForSEO location bridging."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from src.clients.dataforseo.client import DataForSEOClient

logger = logging.getLogger(__name__)

MAPBOX_GEOCODE_V6_FORWARD_URL = "https://api.mapbox.com/search/geocode/v6/forward"
_DFS_LOCATION_CACHE_TTL_SECONDS = 60 * 60
_CITY_LOCATION_TYPES = frozenset({"city"})


class MapboxPlacesError(RuntimeError):
    """Raised when Mapbox autocomplete requests fail."""


@dataclass(slots=True)
class PlaceSuggestion:
    """Compact suggestion model returned by `/api/places/suggest`."""

    place_id: str
    city: str
    region: str
    country: str
    country_iso_code: str
    full_name: str
    latitude: float | None
    longitude: float | None
    dataforseo_location_code: int | None = None
    dataforseo_match_confidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "place_id": self.place_id,
            "city": self.city,
            "region": self.region,
            "country": self.country,
            "country_iso_code": self.country_iso_code,
            "full_name": self.full_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "dataforseo_location_code": self.dataforseo_location_code,
            "dataforseo_match_confidence": self.dataforseo_match_confidence,
        }


def _normalized_text(value: str) -> str:
    chars: list[str] = []
    previous_space = False
    for char in value.lower().strip():
        if char.isalnum():
            chars.append(char)
            previous_space = False
        elif not previous_space:
            chars.append(" ")
            previous_space = True
    return "".join(chars).strip()


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def normalize_mapbox_feature(feature: dict[str, Any]) -> PlaceSuggestion:
    """Convert a Mapbox feature payload into a compact place suggestion."""
    properties = feature.get("properties") or {}
    context = properties.get("context") or {}

    name = str(properties.get("name") or "").strip()
    city = str(properties.get("name_preferred") or name).strip()

    region_ctx = context.get("region") or {}
    country_ctx = context.get("country") or {}

    region_name = str(region_ctx.get("name") or "").strip()
    region_code = str(region_ctx.get("region_code") or "").strip().upper()
    if "-" in region_code:
        region_code = region_code.rsplit("-", 1)[-1]
    region = region_code or region_name
    country = str(country_ctx.get("name") or "").strip()
    country_iso_code = str(country_ctx.get("country_code") or "").strip().upper()

    coordinates = properties.get("coordinates") or {}
    latitude = _coerce_float(coordinates.get("latitude"))
    longitude = _coerce_float(coordinates.get("longitude"))
    if latitude is None or longitude is None:
        geometry = feature.get("geometry") or {}
        geometry_coordinates = geometry.get("coordinates") or []
        if isinstance(geometry_coordinates, list) and len(geometry_coordinates) >= 2:
            longitude = _coerce_float(geometry_coordinates[0])
            latitude = _coerce_float(geometry_coordinates[1])

    full_name = str(
        properties.get("full_address")
        or properties.get("name")
        or city
        or feature.get("id")
        or ""
    ).strip()

    return PlaceSuggestion(
        place_id=str(feature.get("id") or "").strip(),
        city=city,
        region=region,
        country=country,
        country_iso_code=country_iso_code,
        full_name=full_name,
        latitude=latitude,
        longitude=longitude,
    )


def _extract_candidate_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        rows = payload.get("result")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def resolve_dataforseo_location(
    suggestion: PlaceSuggestion,
    location_rows: list[dict[str, Any]],
) -> tuple[int | None, str | None]:
    """Resolve the best DataForSEO location code for a suggestion.

    When multiple DFS rows share the same city name (e.g. Huntsville in AL and
    TX), the state/region part of the DFS ``location_name`` is compared against
    the suggestion's ``full_name`` to pick the correct one.
    """
    city_norm = _normalized_text(suggestion.city)
    full_name_norm = _normalized_text(suggestion.full_name)
    country_norm = suggestion.country_iso_code.upper()
    if not city_norm:
        return None, None

    best_code: int | None = None
    best_score = 0

    for row in location_rows:
        location_name = str(row.get("location_name") or "").strip()
        if not location_name:
            continue

        row_country = str(row.get("country_iso_code") or "").strip().upper()
        if country_norm and row_country and row_country != country_norm:
            continue

        parts = [part.strip() for part in location_name.split(",") if part.strip()]
        primary_name_norm = _normalized_text(parts[0]) if parts else ""
        location_name_norm = _normalized_text(location_name)

        score = 0
        if city_norm and primary_name_norm == city_norm:
            score = 100
            # Tiebreaker: if the DFS row has a state/region part (e.g.
            # "Alabama" in "Huntsville,Alabama,United States"), boost score
            # when it appears in the suggestion's full_name so the correct
            # state wins over same-name cities in other states.
            if len(parts) > 1:
                state_part_norm = _normalized_text(parts[1])
                if state_part_norm and state_part_norm in full_name_norm:
                    score = 110
        elif city_norm and city_norm in location_name_norm:
            score = 75
        elif primary_name_norm and primary_name_norm in full_name_norm:
            score = 55

        if score <= best_score:
            continue

        code = row.get("location_code")
        if not isinstance(code, int):
            continue

        best_score = score
        best_code = code

    if best_code is None:
        return None, None
    if best_score >= 95:
        return best_code, "high"
    if best_score >= 70:
        return best_code, "medium"
    if best_score >= 50:
        return None, "low"
    return None, None


async def fetch_mapbox_place_suggestions(
    *,
    query: str,
    limit: int,
    access_token: str,
    country: str | None = None,
    language: str | None = None,
) -> list[PlaceSuggestion]:
    """Fetch place-level autocomplete suggestions from Mapbox Geocoding v6."""
    params: dict[str, Any] = {
        "q": query,
        "access_token": access_token,
        "types": "place",
        "autocomplete": "true",
        "permanent": "true",
        "limit": limit,
    }
    if country:
        params["country"] = country.lower()
    if language:
        params["language"] = language

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(MAPBOX_GEOCODE_V6_FORWARD_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        logger.error("Mapbox places request failed status=%s", status, exc_info=True)
        raise MapboxPlacesError(f"Mapbox request failed with status {status}") from exc
    except (httpx.HTTPError, ValueError):
        logger.error("Mapbox places request failed unexpectedly", exc_info=True)
        raise MapboxPlacesError("Mapbox request failed") from None

    features = payload.get("features")
    if not isinstance(features, list):
        return []

    return [
        normalize_mapbox_feature(feature)
        for feature in features
        if isinstance(feature, dict)
    ]


class DataForSEOLocationBridge:
    """Best-effort resolver from place suggestions to DataForSEO location codes."""

    def __init__(self, client: DataForSEOClient) -> None:
        self._client = client
        self._cache_lock = asyncio.Lock()
        self._cached_rows: list[dict[str, Any]] = []
        self._city_index: dict[str, list[dict[str, Any]]] = {}
        self._cache_loaded_at = 0.0

    async def _location_rows(self) -> list[dict[str, Any]]:
        now = time.monotonic()
        if self._cache_loaded_at and (now - self._cache_loaded_at) < _DFS_LOCATION_CACHE_TTL_SECONDS:
            return self._cached_rows

        async with self._cache_lock:
            now = time.monotonic()
            if self._cache_loaded_at and (now - self._cache_loaded_at) < _DFS_LOCATION_CACHE_TTL_SECONDS:
                return self._cached_rows

            response = await self._client.locations()
            if response.status != "ok":
                logger.warning("DataForSEO locations() failed: %s", response.error)
                self._cache_loaded_at = time.monotonic()
                return self._cached_rows

            raw_rows = _extract_candidate_rows(response.data)
            rows = [
                r for r in raw_rows
                if str(r.get("location_type", "")).lower() in _CITY_LOCATION_TYPES
            ]

            index: dict[str, list[dict[str, Any]]] = {}
            for row in rows:
                loc_name = str(row.get("location_name") or "")
                parts = [p.strip() for p in loc_name.split(",") if p.strip()]
                if parts:
                    key = _normalized_text(parts[0])
                    if key:
                        index.setdefault(key, []).append(row)

            if rows:
                logger.info(
                    "DFS location bridge loaded %d city rows (from %d total), index keys=%d",
                    len(rows), len(raw_rows), len(index),
                )
            else:
                logger.warning(
                    "DFS location bridge loaded 0 rows — autocomplete codes will be null"
                )
            self._cached_rows = rows
            self._city_index = index
            self._cache_loaded_at = time.monotonic()
            return self._cached_rows

    def _resolve_indexed(self, suggestion: PlaceSuggestion) -> tuple[int | None, str | None]:
        """Resolve DFS location code via pre-built city index — O(1) lookup."""
        city_norm = _normalized_text(suggestion.city)
        if not city_norm:
            return None, None

        candidates = self._city_index.get(city_norm, [])
        if not candidates:
            return None, None

        full_name_norm = _normalized_text(suggestion.full_name)
        country_norm = suggestion.country_iso_code.upper()

        best_code: int | None = None
        best_score = 0

        for row in candidates:
            row_country = str(row.get("country_iso_code") or "").strip().upper()
            if country_norm and row_country and row_country != country_norm:
                continue

            code = row.get("location_code")
            if not isinstance(code, int):
                continue

            location_name = str(row.get("location_name") or "").strip()
            parts = [part.strip() for part in location_name.split(",") if part.strip()]

            score = 100
            if len(parts) > 1:
                state_part_norm = _normalized_text(parts[1])
                if state_part_norm and state_part_norm in full_name_norm:
                    score = 110

            if score > best_score:
                best_score = score
                best_code = code

        if best_code is None:
            return None, None
        return best_code, "high"

    async def enrich(
        self, suggestions: list[PlaceSuggestion]
    ) -> list[PlaceSuggestion]:
        if not suggestions:
            return suggestions

        try:
            await self._location_rows()
        except Exception:
            logger.warning("DataForSEO location bridge failed", exc_info=True)
            return suggestions

        if not self._city_index:
            logger.warning(
                "DFS location bridge has empty index — skipping enrichment for %d suggestions",
                len(suggestions),
            )
            return suggestions

        matched = 0
        for suggestion in suggestions:
            code, confidence = self._resolve_indexed(suggestion)
            suggestion.dataforseo_location_code = code
            suggestion.dataforseo_match_confidence = confidence
            if code is not None:
                matched += 1

        if matched == 0 and suggestions:
            logger.warning(
                "DFS bridge matched 0 of %d suggestions (index_keys=%d)",
                len(suggestions), len(self._city_index),
            )
        else:
            logger.info(
                "DFS bridge matched %d of %d suggestions", matched, len(suggestions),
            )
        return suggestions
