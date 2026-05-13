from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from src.domain.entities import City
from src.domain.ports import GeoLookup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MULTI_SPACE = re.compile(r"\s+")


def _normalize_geo(city: str, state: str | None = None) -> str:
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


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class GeoResolutionError(ValueError):
    """Raised when a city/state cannot be resolved to a valid target."""


@dataclass(frozen=True)
class ResolvedTarget:
    city: City
    metro_name: str
    state_code: str
    location_code: int
    cbsa_code: str
    population: int
    geo_key: str
    place_id: str | None = None
    is_synthetic: bool = False


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GeoResolver:
    def __init__(self, geo_lookup: GeoLookup) -> None:
        self._geo = geo_lookup

    def resolve(
        self,
        city: str,
        state: str | None = None,
        place_id: str | None = None,
        dataforseo_location_code: int | None = None,
    ) -> ResolvedTarget:
        # Normalize state to uppercase or None
        resolved_state = (
            state.strip().upper()
            if isinstance(state, str) and state.strip()
            else None
        )

        # ------------------------------------------------------------------
        # Path 1 — Explicit DataForSEO code provided by caller
        # ------------------------------------------------------------------
        if isinstance(dataforseo_location_code, int) and dataforseo_location_code > 0:
            synthetic_cbsa = (
                f"mapbox:{place_id}"
                if place_id
                else f"manual:{city.lower().replace(' ', '-')}"
            )
            metro_name = city if not resolved_state else f"{city}, {resolved_state}"
            synthetic_city = City(
                city_id=synthetic_cbsa,
                name=city,
                state=resolved_state or "",
                population=0,
                cbsa_code=synthetic_cbsa,
                dataforseo_location_codes=[dataforseo_location_code],
                principal_cities=[city],
            )
            geo_key = _normalize_geo(city, resolved_state)
            return ResolvedTarget(
                city=synthetic_city,
                metro_name=metro_name,
                state_code=resolved_state or "",
                location_code=dataforseo_location_code,
                cbsa_code=synthetic_cbsa,
                population=0,
                geo_key=geo_key,
                place_id=place_id,
                is_synthetic=True,
            )

        # ------------------------------------------------------------------
        # Path 2 — Seed lookup
        # ------------------------------------------------------------------
        result = self._geo.find_by_city(city, state=state)
        if result is not None:
            if not result.dataforseo_location_codes:
                raise GeoResolutionError(
                    f"metro {result.cbsa_code} has no DataForSEO location codes"
                )
            if not resolved_state:
                resolved_state = result.state or ""
            geo_key = _normalize_geo(city, resolved_state)
            return ResolvedTarget(
                city=result,
                metro_name=result.name,
                state_code=resolved_state,
                location_code=result.dataforseo_location_codes[0],
                cbsa_code=result.cbsa_code or result.city_id,
                population=result.population or 0,
                geo_key=geo_key,
                place_id=place_id,
                is_synthetic=False,
            )

        # ------------------------------------------------------------------
        # Path 3 — State-level fallback: borrow DFS code from highest-pop donor
        # ------------------------------------------------------------------
        if resolved_state:
            state_metros = [
                m
                for m in self._geo.all_metros()
                if m.state == resolved_state and m.dataforseo_location_codes
            ]
            if state_metros:
                state_metros.sort(key=lambda m: m.population or 0, reverse=True)
                donor = state_metros[0]
                logger.warning(
                    "City %r not in CBSA seed; falling back to state-level DFS code "
                    "from %s (code=%d) for state=%s",
                    city,
                    donor.name,
                    donor.dataforseo_location_codes[0],
                    resolved_state,
                )
                synthetic_cbsa = (
                    f"mapbox:{place_id}"
                    if place_id
                    else f"fallback:{city.lower().replace(' ', '-')}"
                )
                synthetic_city = City(
                    city_id=synthetic_cbsa,
                    name=city,
                    state=resolved_state,
                    population=0,
                    cbsa_code=synthetic_cbsa,
                    dataforseo_location_codes=[donor.dataforseo_location_codes[0]],
                    principal_cities=[city],
                )
                geo_key = _normalize_geo(city, resolved_state)
                return ResolvedTarget(
                    city=synthetic_city,
                    metro_name=f"{city}, {resolved_state}",
                    state_code=resolved_state,
                    location_code=donor.dataforseo_location_codes[0],
                    cbsa_code=synthetic_cbsa,
                    population=0,
                    geo_key=geo_key,
                    place_id=place_id,
                    is_synthetic=True,
                )

        # ------------------------------------------------------------------
        # No resolution possible
        # ------------------------------------------------------------------
        raise GeoResolutionError(f"no CBSA match for city={city!r} state={state!r}")

    def resolve_batch(self, targets: list[dict]) -> list[ResolvedTarget]:
        resolved: list[ResolvedTarget] = []
        for t in targets:
            try:
                resolved.append(
                    self.resolve(
                        city=t["city"],
                        state=t.get("state"),
                        place_id=t.get("place_id"),
                        dataforseo_location_code=t.get("dataforseo_location_code"),
                    )
                )
            except GeoResolutionError:
                pass
        return resolved
