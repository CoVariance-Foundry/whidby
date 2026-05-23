"""Pure matching helpers for auditing metro DataForSEO location readiness."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import re
from typing import Any


CITY_SPLIT_RE = re.compile(r"\s*[-\u2013\u2014/]\s*")

US_STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}
US_STATE_ABBRS_BY_NAME = {name.upper(): abbr for abbr, name in US_STATE_NAMES.items()}


@dataclass(frozen=True)
class DfsLocation:
    location_code: int
    location_name: str
    city_name: str
    state_code: str
    state_name: str


@dataclass(frozen=True)
class MetroDfsReadinessMatch:
    cbsa_code: str
    cbsa_name: str
    state: str
    population: int | None
    population_class: str
    status: str
    selected_location_code: int | None
    selected_location_name: str | None
    candidate_city: str | None
    reason: str
    existing_codes: tuple[int, ...]

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


def match_metros(
    metros: list[dict[str, Any]],
    dfs_location_rows: list[dict[str, Any]],
) -> list[MetroDfsReadinessMatch]:
    catalog = build_dfs_catalog(dfs_location_rows)
    return [match_metro(metro, catalog) for metro in metros]


def build_dfs_catalog(rows: list[dict[str, Any]]) -> list[DfsLocation]:
    """Return eligible US city-level DFS locations normalized for matching."""
    catalog: list[DfsLocation] = []
    for row in rows:
        if str(row.get("country_iso_code") or "").upper() != "US":
            continue
        if str(row.get("location_type") or "").lower() != "city":
            continue
        code = _int_or_none(row.get("location_code"))
        location_name = str(row.get("location_name") or "").strip()
        city_name, state_code, state_name = _parse_dfs_location_name(location_name)
        if code is None or not city_name or not state_code:
            continue
        catalog.append(
            DfsLocation(
                location_code=code,
                location_name=location_name,
                city_name=city_name,
                state_code=state_code,
                state_name=state_name,
            )
        )
    return catalog


def match_metro(
    metro: dict[str, Any],
    dfs_catalog: list[DfsLocation] | list[dict[str, Any]],
) -> MetroDfsReadinessMatch:
    dfs_catalog = _ensure_catalog(dfs_catalog)
    cbsa_code = str(metro.get("cbsa_code") or "")
    cbsa_name = str(metro.get("cbsa_name") or "")
    state = str(metro.get("state") or "")
    population = _int_or_none(metro.get("population"))
    population_class = str(metro.get("population_class") or "")
    existing_codes = _existing_codes(metro.get("dataforseo_location_codes"))

    principal_cities = candidate_principal_cities(metro)
    cbsa_whole_cities = candidate_cbsa_whole_cities(cbsa_name)
    cbsa_split_cities = candidate_cbsa_split_cities(cbsa_name)
    state_codes = candidate_state_codes(metro)
    existing_matches = _compatible_existing_rows(
        existing_codes,
        dfs_catalog,
        principal_cities=principal_cities,
        cbsa_whole_cities=cbsa_whole_cities,
        state_codes=state_codes,
    )
    if existing_matches:
        selected = existing_matches[0]
        return MetroDfsReadinessMatch(
            cbsa_code=cbsa_code,
            cbsa_name=cbsa_name,
            state=state,
            population=population,
            population_class=population_class,
            status="already_ready",
            selected_location_code=selected.location_code,
            selected_location_name=selected.location_name,
            candidate_city=None,
            reason=(
                "Existing dataforseo_location_codes contains a catalog "
                "location_code compatible with metro city/state candidates."
            ),
            existing_codes=existing_codes,
        )
    if existing_codes:
        return MetroDfsReadinessMatch(
            cbsa_code=cbsa_code,
            cbsa_name=cbsa_name,
            state=state,
            population=population,
            population_class=population_class,
            status="invalid_existing_code",
            selected_location_code=None,
            selected_location_name=None,
            candidate_city=None,
            reason=(
                "Existing dataforseo_location_codes are not present in the DFS "
                "catalog or are incompatible with metro city/state candidates."
            ),
            existing_codes=existing_codes,
        )

    principal_hits = _hits_for_city_tokens(principal_cities, state_codes, dfs_catalog)
    cbsa_whole_hits = _hits_for_city_tokens(
        cbsa_whole_cities,
        state_codes,
        dfs_catalog,
    )
    cbsa_split_hits = _hits_for_city_tokens(
        cbsa_split_cities,
        state_codes,
        dfs_catalog,
    )
    all_hits_by_city: dict[str, list[DfsLocation]] = {}
    all_hits_by_city.update(principal_hits)
    for city, rows in cbsa_whole_hits.items():
        all_hits_by_city.setdefault(city, rows)
    for city, rows in cbsa_split_hits.items():
        all_hits_by_city.setdefault(city, rows)

    ambiguous = _ambiguous_reason(all_hits_by_city)
    if ambiguous:
        return _match_result(
            metro,
            status="ambiguous",
            row=None,
            candidate_city=None,
            reason=ambiguous,
            existing_codes=existing_codes,
        )

    for city, rows in principal_hits.items():
        if len(rows) == 1:
            return _match_result(
                metro,
                status="exact",
                row=rows[0],
                candidate_city=city,
                reason="Single DFS row matched a principal city and metro state.",
                existing_codes=existing_codes,
            )

    for city, rows in cbsa_whole_hits.items():
        if len(rows) == 1:
            return _match_result(
                metro,
                status="strong",
                row=rows[0],
                candidate_city=city,
                reason="Single DFS row matched the whole CBSA prefix and metro state.",
                existing_codes=existing_codes,
            )

    if cbsa_split_hits:
        return _match_result(
            metro,
            status="ambiguous",
            row=None,
            candidate_city=None,
            reason=(
                "Only split CBSA-name city token matches were found; review is "
                "required to avoid false positives from hyphenated city names."
            ),
            existing_codes=existing_codes,
        )

    return _match_result(
        metro,
        status="no_match",
        row=None,
        candidate_city=None,
        reason="No eligible US city-level DFS row matched candidate city and state tokens.",
        existing_codes=existing_codes,
    )


def summarize_matches(matches: list[MetroDfsReadinessMatch]) -> dict[str, Any]:
    by_status = Counter(match.status for match in matches)
    by_population_class_status: dict[str, Counter[str]] = defaultdict(Counter)
    residual_review = Counter(
        residual_review_classification(match.status)
        for match in matches
        if match.status in RESIDUAL_STATUSES
    )
    for match in matches:
        population_class = match.population_class or "<unknown>"
        by_population_class_status[population_class][match.status] += 1
    return {
        "total": len(matches),
        "by_status": dict(sorted(by_status.items())),
        "by_population_class_status": {
            population_class: dict(sorted(status_counts.items()))
            for population_class, status_counts in sorted(
                by_population_class_status.items()
            )
        },
        "residual_review_classification": dict(sorted(residual_review.items())),
    }


RESIDUAL_STATUSES = {"ambiguous", "invalid_existing_code", "no_match"}


def residual_review_classification(status: str) -> str:
    return {
        "ambiguous": "approve",
        "invalid_existing_code": "correct",
        "no_match": "needs_alternate_target",
    }.get(status, "exclude")


def residual_seed_policy(status: str) -> str:
    if status in RESIDUAL_STATUSES:
        return "excluded_until_reviewed"
    return "eligible_if_selected"


def candidate_principal_cities(metro: dict[str, Any]) -> list[str]:
    return _dedupe_preserve_order(_city_values(metro.get("principal_cities")))


def candidate_cbsa_cities(cbsa_name: str) -> list[str]:
    return _dedupe_preserve_order(
        [*candidate_cbsa_whole_cities(cbsa_name), *candidate_cbsa_split_cities(cbsa_name)]
    )


def candidate_cbsa_whole_cities(cbsa_name: str) -> list[str]:
    prefix = cbsa_name.split(",", 1)[0]
    return _dedupe_preserve_order([prefix.strip()] if prefix.strip() else [])


def candidate_cbsa_split_cities(cbsa_name: str) -> list[str]:
    prefix = cbsa_name.split(",", 1)[0]
    return _dedupe_preserve_order(
        token.strip() for token in CITY_SPLIT_RE.split(prefix) if token.strip()
    )


def candidate_state_codes(metro: dict[str, Any]) -> set[str]:
    tokens: list[str] = []
    state = str(metro.get("state") or "").strip()
    if state:
        tokens.append(state)
    cbsa_name = str(metro.get("cbsa_name") or "")
    if "," in cbsa_name:
        suffix = cbsa_name.split(",", 1)[1]
        tokens.extend(
            token.strip()
            for token in CITY_SPLIT_RE.split(suffix)
            if token.strip()
        )
    codes = {_state_token_to_abbr(token) for token in tokens}
    return {code for code in codes if code}


def _hits_for_city_tokens(
    cities: list[str],
    state_codes: set[str],
    dfs_catalog: list[DfsLocation],
) -> dict[str, list[DfsLocation]]:
    hits: dict[str, list[DfsLocation]] = {}
    for city in cities:
        normalized_city = _normalize_name(city)
        rows = [
            row
            for row in dfs_catalog
            if _normalize_name(row.city_name) == normalized_city
            and row.state_code in state_codes
        ]
        if rows:
            hits[city] = rows
    return hits


def _compatible_existing_rows(
    existing_codes: tuple[int, ...],
    dfs_catalog: list[DfsLocation],
    *,
    principal_cities: list[str],
    cbsa_whole_cities: list[str],
    state_codes: set[str],
) -> list[DfsLocation]:
    candidate_names = {
        _normalize_name(city) for city in [*principal_cities, *cbsa_whole_cities]
    }
    existing_code_set = set(existing_codes)
    return [
        row
        for row in dfs_catalog
        if row.location_code in existing_code_set
        and row.state_code in state_codes
        and _normalize_name(row.city_name) in candidate_names
    ]


def _ensure_catalog(rows: list[DfsLocation] | list[dict[str, Any]]) -> list[DfsLocation]:
    if not rows:
        return []
    first = rows[0]
    if isinstance(first, DfsLocation):
        return rows  # type: ignore[return-value]
    return build_dfs_catalog(rows)  # type: ignore[arg-type]


def _ambiguous_reason(hits_by_city: dict[str, list[DfsLocation]]) -> str | None:
    if any(len(rows) > 1 for rows in hits_by_city.values()):
        return "Multiple plausible DFS rows remained after city/state/country filtering."
    distinct_codes = {
        rows[0].location_code for rows in hits_by_city.values() if len(rows) == 1
    }
    if len(distinct_codes) > 1:
        return "Multiple candidate city tokens produced different plausible DFS codes."
    return None


def _match_result(
    metro: dict[str, Any],
    *,
    status: str,
    row: DfsLocation | None,
    candidate_city: str | None,
    reason: str,
    existing_codes: tuple[int, ...],
) -> MetroDfsReadinessMatch:
    return MetroDfsReadinessMatch(
        cbsa_code=str(metro.get("cbsa_code") or ""),
        cbsa_name=str(metro.get("cbsa_name") or ""),
        state=str(metro.get("state") or ""),
        population=_int_or_none(metro.get("population")),
        population_class=str(metro.get("population_class") or ""),
        status=status,
        selected_location_code=row.location_code if row else None,
        selected_location_name=row.location_name if row else None,
        candidate_city=candidate_city,
        reason=reason,
        existing_codes=existing_codes,
    )


def _parse_dfs_location_name(location_name: str) -> tuple[str, str, str]:
    parts = [part.strip() for part in location_name.split(",")]
    if len(parts) < 2:
        return "", "", ""
    city_name = parts[0]
    state_token = parts[1]
    state_code = _state_token_to_abbr(state_token)
    state_name = US_STATE_NAMES.get(state_code or "", state_token)
    return city_name, state_code or "", state_name


def _state_token_to_abbr(token: str) -> str | None:
    normalized = token.strip().upper().replace(".", "")
    if normalized in US_STATE_NAMES:
        return normalized
    return US_STATE_ABBRS_BY_NAME.get(normalized)


def _city_values(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(value).strip() for value in raw if str(value).strip()]
    if isinstance(raw, str):
        return [
            value.strip()
            for value in re.split(r"[;,]", raw)
            if value.strip()
        ]
    return [str(raw).strip()] if str(raw).strip() else []


def _existing_codes(raw: Any) -> tuple[int, ...]:
    if raw is None:
        return ()
    values = raw if isinstance(raw, list) else [raw]
    codes = [_int_or_none(value) for value in values]
    return tuple(code for code in codes if code is not None)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _dedupe_preserve_order(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = _normalize_name(str(value))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(str(value).strip())
    return result
