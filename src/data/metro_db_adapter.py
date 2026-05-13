from __future__ import annotations

from src.data.metro_db import Metro, MetroDB
from src.domain.entities import City


class MetroDBGeoLookup:
    """Implements GeoLookup port using the existing MetroDB."""

    def __init__(self, metro_db: MetroDB) -> None:
        self._db = metro_db

    def find_by_city(self, city: str, state: str | None = None) -> City | None:
        metro = self._db.find_by_city(city, state=state)
        if metro is None:
            return None
        return _metro_to_city(metro)

    def all_metros(self) -> list[City]:
        return [_metro_to_city(m) for m in self._db.all_metros()]


def _metro_to_city(metro: Metro) -> City:
    return City(
        city_id=metro.cbsa_code,
        name=metro.cbsa_name,
        state=metro.state,
        population=metro.population,
        cbsa_code=metro.cbsa_code,
        dataforseo_location_codes=list(metro.dataforseo_location_codes),
        principal_cities=list(metro.principal_cities),
    )
