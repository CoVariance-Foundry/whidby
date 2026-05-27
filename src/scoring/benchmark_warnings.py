"""Canonical product-facing warning codes for benchmark-backed scoring."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.scoring.benchmark_repository import SeoBenchmarkCell

METRIC_MISSING = "metric_missing"
METRIC_UNDERSAMPLED = "metric_undersampled"
POOLED_BENCHMARK = "pooled_benchmark"
STALE_EVIDENCE = "stale_evidence"
LOCAL_IDENTIFIER_MISSING = "local_identifier_missing"
DEMAND_SOURCE_CANDIDATE = "demand_source_candidate"
BENCHMARK_LINEAGE_MISSING = "benchmark_lineage_missing"

CANONICAL_WARNING_CODES: tuple[str, ...] = (
    METRIC_MISSING,
    METRIC_UNDERSAMPLED,
    POOLED_BENCHMARK,
    STALE_EVIDENCE,
    LOCAL_IDENTIFIER_MISSING,
    DEMAND_SOURCE_CANDIDATE,
    BENCHMARK_LINEAGE_MISSING,
)

LOW_CONFIDENCE_LABELS = {"low", "insufficient"}
POOLED_BENCHMARK_MODES = {
    "pooled_population",
    "pooled_service_group",
    "global_service",
}
DEFAULT_MIN_BENCHMARK_SAMPLE_SIZE = 8

_MISSING_STATUSES = {
    "metric_missing",
    "missing",
    "no_evidence",
    "not_attempted",
}
_UNDERSAMPLED_STATUSES = {
    "metric_undersampled",
    "undersampled",
    "sparse",
    "low",
    "insufficient",
}
_STALE_STATUSES = {
    "stale",
    "stale_evidence",
    "wrong_run",
    "wrong-run",
    "wrong_benchmark_run",
    "benchmark_run_mismatch",
}


def warning_code_from_metric_status(status: Any) -> str | None:
    """Map audit/read-model metric-sufficiency states to product warning codes."""
    normalized = _normalized_label(status)
    if normalized in _MISSING_STATUSES:
        return METRIC_MISSING
    if normalized in _UNDERSAMPLED_STATUSES:
        return METRIC_UNDERSAMPLED
    if normalized in _STALE_STATUSES:
        return STALE_EVIDENCE
    return None


def warning_codes_from_benchmark(
    benchmark: SeoBenchmarkCell | None,
    *,
    min_sample_size: int = DEFAULT_MIN_BENCHMARK_SAMPLE_SIZE,
) -> list[str]:
    """Derive canonical warning codes from one benchmark cell."""
    if benchmark is None:
        return [BENCHMARK_LINEAGE_MISSING, METRIC_MISSING]

    codes: list[str] = []
    if (
        benchmark.confidence_label in LOW_CONFIDENCE_LABELS
        or benchmark.sample_size_metros < min_sample_size
    ):
        codes.append(METRIC_UNDERSAMPLED)
    if benchmark.benchmark_mode in POOLED_BENCHMARK_MODES:
        codes.append(POOLED_BENCHMARK)
    if not (
        _has_text(benchmark.benchmark_run_id)
        and _has_text(benchmark.formula_version)
        and _has_text(benchmark.sample_frame_version)
    ):
        codes.append(BENCHMARK_LINEAGE_MISSING)
    codes.extend(warning_codes_from_metric_rollup(benchmark.metric_confidence_rollup))
    return dedupe_warning_codes(codes)


def warning_codes_from_mapping(
    row: Mapping[str, Any],
    *,
    min_sample_size: int = DEFAULT_MIN_BENCHMARK_SAMPLE_SIZE,
) -> list[str]:
    """Derive canonical warning codes from persisted score/read-model rows."""
    codes: list[str] = []
    for key in ("warning_codes", "evidence_warning_codes"):
        codes.extend(_warning_items(row.get(key)))

    confidence = _normalized_label(row.get("benchmark_confidence") or row.get("confidence_label"))
    if confidence in LOW_CONFIDENCE_LABELS:
        codes.append(METRIC_UNDERSAMPLED)

    if _truthy(row.get("benchmark_undersampled")):
        codes.append(METRIC_UNDERSAMPLED)

    sample_size = _optional_int(
        row.get("benchmark_sample_size", row.get("sample_size_metros"))
    )
    if sample_size is not None and sample_size < min_sample_size:
        codes.append(METRIC_UNDERSAMPLED)

    if _normalized_label(row.get("benchmark_mode")) in POOLED_BENCHMARK_MODES:
        codes.append(POOLED_BENCHMARK)

    if _has_any_key(row, ("benchmark_run_id", "formula_version", "sample_frame_version")):
        if not (
            _has_text(row.get("benchmark_run_id"))
            and _has_text(row.get("formula_version"))
            and _has_text(row.get("sample_frame_version"))
        ):
            codes.append(BENCHMARK_LINEAGE_MISSING)

    if _truthy(row.get("stale_evidence")) or _truthy(row.get("evidence_stale")):
        codes.append(STALE_EVIDENCE)
    if _truthy(row.get("local_identifier_missing")):
        codes.append(LOCAL_IDENTIFIER_MISSING)
    if _truthy(row.get("demand_source_candidate")):
        codes.append(DEMAND_SOURCE_CANDIDATE)

    for key in ("metric_sufficiency_status", "benchmark_metric_status"):
        code = warning_code_from_metric_status(row.get(key))
        if code:
            codes.append(code)

    codes.extend(warning_codes_from_metric_rollup(row.get("metric_confidence_rollup")))
    return dedupe_warning_codes(codes)


def warning_codes_from_metric_rollup(value: Any) -> list[str]:
    """Extract warning codes from per-metric sufficiency rollups."""
    if not isinstance(value, Mapping):
        return []

    codes: list[str] = []
    for detail in value.values():
        if isinstance(detail, Mapping):
            code = warning_code_from_metric_status(
                detail.get("status")
                or detail.get("metric_status")
                or detail.get("sufficiency_status")
            )
            if code:
                codes.append(code)
            confidence = _normalized_label(detail.get("confidence_label"))
            if confidence in LOW_CONFIDENCE_LABELS:
                codes.append(METRIC_UNDERSAMPLED)
            if _truthy(detail.get("stale_evidence")) or _truthy(detail.get("wrong_run")):
                codes.append(STALE_EVIDENCE)
        else:
            code = warning_code_from_metric_status(detail)
            if code:
                codes.append(code)
    return dedupe_warning_codes(codes)


def dedupe_warning_codes(codes: Iterable[Any]) -> list[str]:
    """Return non-empty warning codes once, preserving first-seen order."""
    deduped: list[str] = []
    seen: set[str] = set()
    for code in codes:
        if not isinstance(code, str):
            continue
        normalized = code.strip()
        if not normalized or normalized in seen:
            continue
        deduped.append(normalized)
        seen.add(normalized)
    return deduped


def _warning_items(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        code = value.get("code")
        return [code] if isinstance(code, str) else []
    if not isinstance(value, Iterable):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            items.append(item)
        elif isinstance(item, Mapping) and isinstance(item.get("code"), str):
            items.append(item["code"])
    return items


def _has_any_key(row: Mapping[str, Any], keys: tuple[str, ...]) -> bool:
    return any(key in row for key in keys)


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalized_label(value: Any) -> str:
    return str(value or "").strip().lower()


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y"}
    return bool(value)
