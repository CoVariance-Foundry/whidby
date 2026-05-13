"""Pure repository contract for V2 seo_benchmarks cells."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Mapping, Protocol

BenchmarkConfidence = Literal["high", "medium", "low", "insufficient"]
_CONFIDENCE_VALUES: set[str] = {"high", "medium", "low", "insufficient"}


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _required_int(row: Mapping[str, Any], key: str) -> int:
    value = row.get(key)
    if value is None:
        raise ValueError(f"Missing required benchmark column: {key}")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"Empty required benchmark column: {key}")
    return int(value)


def _required_text(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if value is None:
        raise ValueError(f"Missing required benchmark column: {key}")
    text = str(value).strip()
    if not text:
        raise ValueError(f"Empty required benchmark column: {key}")
    return text


def _confidence(value: Any) -> BenchmarkConfidence:
    label = str(value or "").strip()
    if label not in _CONFIDENCE_VALUES:
        raise ValueError(f"Unsupported benchmark confidence: {label!r}")
    return label  # type: ignore[return-value]


@dataclass(frozen=True)
class SeoBenchmarkCell:
    """One `seo_benchmarks` cell keyed by niche and population class."""

    niche_normalized: str
    population_class: str
    naics_code: str | None
    p25_total_volume_per_capita: float | None
    median_total_volume_per_capita: float | None
    p75_total_volume_per_capita: float | None
    p25_avg_cpc: float | None
    median_avg_cpc: float | None
    p75_avg_cpc: float | None
    median_top3_review_count_min: int | None
    median_top3_review_velocity: float | None
    pct_with_local_pack: float | None
    median_aggregator_count: float | None
    median_local_biz_count: float | None
    median_establishments_per_100k: float | None
    median_lsa_present_rate: float | None
    median_ads_present_rate: float | None
    median_aio_trigger_rate: float | None
    sample_size_metros: int
    sample_size_observations: int
    confidence_label: BenchmarkConfidence
    fact_window_start: str | None = None
    fact_window_end: str | None = None

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "SeoBenchmarkCell":
        """Build a benchmark cell from a PostgREST/Supabase row."""
        return cls(
            niche_normalized=_required_text(row, "niche_normalized"),
            population_class=_required_text(row, "population_class"),
            naics_code=(
                str(row["naics_code"]).strip()
                if row.get("naics_code") is not None and str(row["naics_code"]).strip()
                else None
            ),
            p25_total_volume_per_capita=_float_or_none(row.get("p25_total_volume_per_capita")),
            median_total_volume_per_capita=_float_or_none(
                row.get("median_total_volume_per_capita")
            ),
            p75_total_volume_per_capita=_float_or_none(row.get("p75_total_volume_per_capita")),
            p25_avg_cpc=_float_or_none(row.get("p25_avg_cpc")),
            median_avg_cpc=_float_or_none(row.get("median_avg_cpc")),
            p75_avg_cpc=_float_or_none(row.get("p75_avg_cpc")),
            median_top3_review_count_min=_int_or_none(row.get("median_top3_review_count_min")),
            median_top3_review_velocity=_float_or_none(row.get("median_top3_review_velocity")),
            pct_with_local_pack=_float_or_none(row.get("pct_with_local_pack")),
            median_aggregator_count=_float_or_none(row.get("median_aggregator_count")),
            median_local_biz_count=_float_or_none(row.get("median_local_biz_count")),
            median_establishments_per_100k=_float_or_none(
                row.get("median_establishments_per_100k")
            ),
            median_lsa_present_rate=_float_or_none(row.get("median_lsa_present_rate")),
            median_ads_present_rate=_float_or_none(row.get("median_ads_present_rate")),
            median_aio_trigger_rate=_float_or_none(row.get("median_aio_trigger_rate")),
            sample_size_metros=_required_int(row, "sample_size_metros"),
            sample_size_observations=_required_int(row, "sample_size_observations"),
            confidence_label=_confidence(row.get("confidence_label")),
            fact_window_start=(
                str(row["fact_window_start"]) if row.get("fact_window_start") is not None else None
            ),
            fact_window_end=(
                str(row["fact_window_end"]) if row.get("fact_window_end") is not None else None
            ),
        )

    @property
    def is_undersampled(self) -> bool:
        """True when V2 should show preliminary/limited benchmark messaging."""
        return self.confidence_label in {"low", "insufficient"} or self.sample_size_metros < 8


class SeoBenchmarkRepository(Protocol):
    """Read boundary for V2 scoring benchmark cells."""

    def get(
        self,
        *,
        niche_normalized: str,
        population_class: str,
    ) -> SeoBenchmarkCell | None:
        """Return the benchmark cell for one `(niche, population_class)` key."""
        ...
