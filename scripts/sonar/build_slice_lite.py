"""Build a Sonar slice-lite CellRecord from existing Widby benchmark tables."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlreq


DEFAULT_NAICS_CODE = "238220"
DEFAULT_NAICS_VERSION = "NAICS2017"
DEFAULT_CBSA_CODE = "31080"
DEFAULT_NICHE_NORMALIZED = "plumber"
SCORE_VERSION = "sonar-lite-0.1"
SLICE_LITE_WARNINGS = [
    "slice_lite_no_nes",
    "slice_lite_no_bds",
    "slice_lite_no_trends",
    "slice_lite_no_geo_crosswalk",
    "slice_lite_no_residual_model",
]

SUPABASE_URL = os.environ.get(
    "BENCHMARK_SUPABASE_URL",
    "https://wuybidpvqhhgkukpyyhq.supabase.co",
)
SUPABASE_KEY = (
    os.environ.get("BENCHMARK_SUPABASE_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)


def utc_now_iso() -> str:
    """Return a compact UTC timestamp for ad-hoc helper calls."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def deterministic_record_ts(year: int, fact_window_end: str | None) -> str:
    """Return a stable record timestamp from source vintage, not wall-clock time."""
    if fact_window_end:
        return f"{fact_window_end}T00:00:00Z"
    return f"{year}-12-31T00:00:00Z"


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """Clamp a numeric score to an inclusive range."""
    return max(lower, min(upper, value))


def compute_z_score_gap(
    *,
    value: float | int | None,
    benchmark: float | int | None,
    spread: float | int | None,
) -> dict[str, float | None]:
    """Compute a benchmark gap and z-like spread-normalized distance."""
    if value is None or benchmark is None:
        return {"value": value, "benchmark": benchmark, "gap": None, "z_score": None}

    gap = float(value) - float(benchmark)
    if spread is None or float(spread) == 0.0:
        z_score = None
    else:
        z_score = gap / float(spread)

    return {
        "value": float(value),
        "benchmark": float(benchmark),
        "gap": round(gap, 6),
        "z_score": round(z_score, 6) if z_score is not None else None,
    }


def shape_evidence_payload(
    *,
    raw_inputs: dict[str, Any],
    source: str,
    vintage: str,
    computed_at: str | None = None,
    suppression_flag: bool = False,
) -> dict[str, Any]:
    """Shape consistent metric evidence without requiring network access."""
    timestamp = computed_at or utc_now_iso()
    return {
        "raw_inputs": raw_inputs,
        "source": source,
        "vintage": vintage,
        "computed_at": timestamp,
        "suppression_flag": suppression_flag,
    }


def build_metric_block(
    *,
    value: int | float | None,
    raw_inputs: dict[str, Any],
    source: str,
    vintage: str,
    suppression_flag: bool = False,
    computed_at: str | None = None,
) -> dict[str, Any]:
    """Return a CellRecord metric block with inline provenance."""
    evidence = shape_evidence_payload(
        raw_inputs=raw_inputs,
        source=source,
        vintage=vintage,
        computed_at=computed_at,
        suppression_flag=suppression_flag,
    )
    return {
        "value": value,
        **evidence,
        "evidence": evidence,
    }


def compute_opportunity_score(
    *,
    searches_per_household: float,
    establishments_per_10k_pop: float,
    avg_cpc: float,
    commercial_intent_share: float,
    serp_consolidation_index: float,
) -> float:
    """Compute the slice-lite opportunity score from available source layers."""
    demand_supply = clamp(
        (searches_per_household / 0.02) - (establishments_per_10k_pop / 10.0)
    )
    intent = clamp(commercial_intent_share)
    monetization = clamp(avg_cpc / 50.0)
    serp_entry = clamp(1.0 - serp_consolidation_index)
    score = (
        0.40 * demand_supply
        + 0.20 * intent
        + 0.20 * monetization
        + 0.20 * serp_entry
    )
    return round(clamp(score), 4)


def compute_lite_score(
    *,
    searches_per_household: float,
    establishments_per_10k_pop: float,
    avg_cpc: float,
    commercial_intent_share: float,
    serp_consolidation_index: float,
) -> float:
    """Backward-compatible alias for the slice-lite opportunity score."""
    return compute_opportunity_score(
        searches_per_household=searches_per_household,
        establishments_per_10k_pop=establishments_per_10k_pop,
        avg_cpc=avg_cpc,
        commercial_intent_share=commercial_intent_share,
        serp_consolidation_index=serp_consolidation_index,
    )


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def build_seo_rollup(seo_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate keyword-grain seo_facts rows into the slice-lite SEO inputs."""
    volume = sum(_as_int(row.get("search_volume_monthly")) for row in seo_rows)
    volume_with_cpc = sum(
        _as_int(row.get("search_volume_monthly"))
        for row in seo_rows
        if row.get("cpc_usd") is not None
    )
    weighted_cpc_numerator = sum(
        _as_int(row.get("search_volume_monthly")) * _as_float(row.get("cpc_usd"))
        for row in seo_rows
        if row.get("cpc_usd") is not None
    )
    row_count = len(seo_rows)
    cpc_count = sum(1 for row in seo_rows if row.get("cpc_usd") is not None)
    local_pack_count = sum(1 for row in seo_rows if row.get("local_pack_present") is True)
    avg_aggregators = _safe_div(
        sum(_as_float(row.get("aggregator_count_top10")) for row in seo_rows),
        row_count,
    )
    fact_dates = [row.get("snapshot_date") for row in seo_rows if row.get("snapshot_date")]

    return {
        "keyword_rows": row_count,
        "cluster_monthly_volume": volume,
        "commercial_transactional_volume": volume,
        "avg_cpc_unweighted": _safe_div(
            sum(_as_float(row.get("cpc_usd")) for row in seo_rows),
            cpc_count,
        ),
        "avg_cpc_volume_weighted": _safe_div(weighted_cpc_numerator, volume_with_cpc),
        "serp_local_pack_rate": _safe_div(local_pack_count, row_count),
        "avg_aggregator_count_top10": avg_aggregators,
        "fact_window_end": max(fact_dates) if fact_dates else None,
    }


def build_benchmark_gaps(
    *,
    total_volume_per_capita: float,
    establishments_per_100k: float,
    avg_cpc: float,
    benchmark: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build benchmark-relative z-score/gap diagnostics when a cell exists."""
    if not benchmark:
        return {}

    volume_spread = _as_float(benchmark.get("p75_total_volume_per_capita")) - _as_float(
        benchmark.get("p25_total_volume_per_capita")
    )
    cpc_spread = _as_float(benchmark.get("p75_avg_cpc")) - _as_float(
        benchmark.get("p25_avg_cpc")
    )
    return {
        "total_volume_per_capita": compute_z_score_gap(
            value=total_volume_per_capita,
            benchmark=benchmark.get("median_total_volume_per_capita"),
            spread=volume_spread,
        ),
        "establishments_per_100k": compute_z_score_gap(
            value=establishments_per_100k,
            benchmark=benchmark.get("median_establishments_per_100k"),
            spread=benchmark.get("median_establishments_per_100k"),
        ),
        "avg_cpc": compute_z_score_gap(
            value=avg_cpc,
            benchmark=benchmark.get("median_avg_cpc"),
            spread=cpc_spread,
        ),
        "benchmark_confidence": benchmark.get("confidence_label"),
        "benchmark_sample_size_metros": benchmark.get("sample_size_metros"),
    }


def build_cell_record(
    *,
    metro: dict[str, Any],
    cbp: dict[str, Any],
    seo: dict[str, Any],
    peer_count: int,
    year: int,
    benchmark: dict[str, Any] | None = None,
    naics_code: str = DEFAULT_NAICS_CODE,
    naics_version: str = DEFAULT_NAICS_VERSION,
) -> dict[str, Any]:
    """Build a deterministic slice-lite CellRecord from source table rows."""
    population = _as_float(metro.get("population"))
    households = _as_float(metro.get("households"))
    establishments = _as_float(cbp.get("est"))
    employees = _as_float(cbp.get("emp"))
    payroll_thousands = _as_float(cbp.get("ap"))
    volume = _as_float(seo.get("cluster_monthly_volume"))
    avg_cpc = _as_float(seo.get("avg_cpc_volume_weighted") or seo.get("avg_cpc_unweighted"))
    commercial_intent_share = _safe_div(
        _as_float(seo.get("commercial_transactional_volume")),
        max(volume, 1.0),
    )
    establishments_per_10k = _safe_div(establishments, _safe_div(population, 10_000.0))
    establishments_per_100k = establishments_per_10k * 10.0
    searches_per_household = _safe_div(volume, max(households, 1.0))
    total_volume_per_capita = _safe_div(volume, max(population, 1.0))
    avg_employees_per_estab = _safe_div(employees, max(establishments, 1.0))
    payroll_per_emp = _safe_div(payroll_thousands * 1000.0, max(employees, 1.0))
    top_size_class_share = _safe_div(
        sum(
            _as_float(cbp.get(field))
            for field in ("n50_99", "n100_249", "n250_499", "n500_999", "n1000")
        ),
        max(establishments, 1.0),
    )
    serp_consolidation_index = clamp(_as_float(seo.get("avg_aggregator_count_top10")) / 10.0)
    score = compute_opportunity_score(
        searches_per_household=searches_per_household,
        establishments_per_10k_pop=establishments_per_10k,
        avg_cpc=avg_cpc,
        commercial_intent_share=commercial_intent_share,
        serp_consolidation_index=serp_consolidation_index,
    )
    computed_at = deterministic_record_ts(year, seo.get("fact_window_end"))
    acs_source = f"acs_{metro.get('acs_vintage') or year}_5yr"
    cbp_source = f"cbp_{year}"
    suppression_flag = bool(cbp.get("suppressed"))

    return {
        "cell_id": f"{naics_code}__msa__{metro['cbsa_code']}__{year}",
        "naics_code": naics_code,
        "naics_version": naics_version,
        "geo_id": metro["cbsa_code"],
        "geo_level": "msa",
        "geo_name": metro["cbsa_name"],
        "year": year,
        "extract_run_ts": computed_at,
        "supply": {
            "establishments_per_10k_pop": build_metric_block(
                value=round(establishments_per_10k, 4),
                raw_inputs={"estab": cbp.get("est"), "pop": metro.get("population")},
                source=f"{cbp_source} + {acs_source}",
                vintage=str(year),
                suppression_flag=suppression_flag,
                computed_at=computed_at,
            ),
            "avg_employees_per_estab": build_metric_block(
                value=round(avg_employees_per_estab, 4),
                raw_inputs={"emp": cbp.get("emp"), "estab": cbp.get("est")},
                source=cbp_source,
                vintage=str(year),
                suppression_flag=suppression_flag,
                computed_at=computed_at,
            ),
            "top_size_class_share": build_metric_block(
                value=round(top_size_class_share, 4),
                raw_inputs={
                    "n50_99": cbp.get("n50_99"),
                    "n100_249": cbp.get("n100_249"),
                    "n250_499": cbp.get("n250_499"),
                    "n500_999": cbp.get("n500_999"),
                    "n1000": cbp.get("n1000"),
                    "estab": cbp.get("est"),
                },
                source=cbp_source,
                vintage=str(year),
                suppression_flag=suppression_flag,
                computed_at=computed_at,
            ),
        },
        "demand": {
            "cluster_monthly_volume": build_metric_block(
                value=int(volume),
                raw_inputs={"seo_fact_rows": seo.get("keyword_rows")},
                source="seo_facts",
                vintage=str(seo.get("fact_window_end")),
                computed_at=computed_at,
            ),
            "commercial_intent_share": build_metric_block(
                value=round(commercial_intent_share, 4),
                raw_inputs={
                    "commercial_transactional_volume": seo.get(
                        "commercial_transactional_volume"
                    ),
                    "cluster_monthly_volume": seo.get("cluster_monthly_volume"),
                },
                source="seo_facts + intent_classifier",
                vintage=str(seo.get("fact_window_end")),
                computed_at=computed_at,
            ),
            "searches_per_household": build_metric_block(
                value=round(searches_per_household, 6),
                raw_inputs={
                    "cluster_monthly_volume": seo.get("cluster_monthly_volume"),
                    "households": metro.get("households"),
                },
                source=f"seo_facts + {acs_source}",
                vintage=str(year),
                computed_at=computed_at,
            ),
        },
        "monetization_capacity": {
            "median_hh_income": build_metric_block(
                value=metro.get("median_household_income_usd"),
                raw_inputs={
                    "median_household_income_usd": metro.get(
                        "median_household_income_usd"
                    )
                },
                source=acs_source,
                vintage=str(year),
                computed_at=computed_at,
            ),
            "owner_occupied_share": build_metric_block(
                value=_as_float(metro.get("owner_occupancy_rate")),
                raw_inputs={"owner_occupancy_rate": metro.get("owner_occupancy_rate")},
                source=acs_source,
                vintage=str(year),
                computed_at=computed_at,
            ),
            "payroll_per_emp": build_metric_block(
                value=round(payroll_per_emp, 2),
                raw_inputs={"payroll_thousands": cbp.get("ap"), "emp": cbp.get("emp")},
                source=cbp_source,
                vintage=str(year),
                suppression_flag=suppression_flag,
                computed_at=computed_at,
            ),
        },
        "seo_economics": {
            "cpc_top_low_weighted": build_metric_block(
                value=round(avg_cpc, 2),
                raw_inputs={"cluster_monthly_volume": seo.get("cluster_monthly_volume")},
                source="seo_facts.cpc_usd",
                vintage=str(seo.get("fact_window_end")),
                computed_at=computed_at,
            ),
            "serp_local_pack_rate": build_metric_block(
                value=round(_as_float(seo.get("serp_local_pack_rate")), 4),
                raw_inputs={"keyword_rows": seo.get("keyword_rows")},
                source="seo_facts.local_pack_present",
                vintage=str(seo.get("fact_window_end")),
                computed_at=computed_at,
            ),
            "serp_consolidation_index": build_metric_block(
                value=round(serp_consolidation_index, 4),
                raw_inputs={
                    "avg_aggregator_count_top10": seo.get("avg_aggregator_count_top10")
                },
                source="seo_facts.aggregator_count_top10",
                vintage=str(seo.get("fact_window_end")),
                computed_at=computed_at,
            ),
        },
        "derived_ratios": {
            "monetization_headroom": build_metric_block(
                value=round(
                    _safe_div(
                        avg_cpc * commercial_intent_share,
                        max(payroll_per_emp / 1000.0, 0.01),
                    ),
                    4,
                ),
                raw_inputs={
                    "avg_cpc": round(avg_cpc, 4),
                    "commercial_intent_share": round(commercial_intent_share, 4),
                    "payroll_per_emp": round(payroll_per_emp, 2),
                },
                source="derived",
                vintage=str(year),
                computed_at=computed_at,
            )
        },
        "benchmark_gaps": build_benchmark_gaps(
            total_volume_per_capita=total_volume_per_capita,
            establishments_per_100k=establishments_per_100k,
            avg_cpc=avg_cpc,
            benchmark=benchmark,
        ),
        "residuals": {},
        "data_quality": {
            "suppression_count": 1 if suppression_flag else 0,
            "suppressed_fields": ["cbp"] if suppression_flag else [],
            "imputed_fields": [],
            "freshness_lag_days": None,
            "warnings": SLICE_LITE_WARNINGS,
            f"peer_count_{naics_code}": peer_count,
        },
        "score": {
            "underserved_score": score,
            "opportunity_score": score,
            "score_components": {
                "searches_per_household": round(searches_per_household, 6),
                "establishments_per_10k_pop": round(establishments_per_10k, 4),
                "commercial_intent_share": round(commercial_intent_share, 4),
                "avg_cpc": round(avg_cpc, 2),
                "serp_consolidation_index": round(serp_consolidation_index, 4),
            },
            "score_version": SCORE_VERSION,
        },
    }


def _require_supabase_key() -> str:
    if not SUPABASE_KEY:
        raise RuntimeError("BENCHMARK_SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY is required")
    return SUPABASE_KEY


def _postgrest_request(
    path: str,
    *,
    method: str = "GET",
    payload: Any = None,
    headers: dict[str, str] | None = None,
) -> Any:
    key = _require_supabase_key()
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if headers:
        request_headers.update(headers)
    req = urlreq.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with urlreq.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urlerror.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"PostgREST {exc.code} for {path}: {body}") from None
    if not body:
        return None
    return json.loads(body)


def postgrest_count(path: str) -> int:
    """Return an exact PostgREST count without fetching all matching rows."""
    key = _require_supabase_key()
    req = urlreq.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Prefer": "count=exact",
            "Range": "0-0",
        },
        method="GET",
    )
    try:
        with urlreq.urlopen(req, timeout=60) as response:
            content_range = response.headers.get("Content-Range", "")
    except urlerror.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"PostgREST {exc.code} for {path}: {body}") from None
    if "/" not in content_range:
        raise RuntimeError(f"PostgREST count missing Content-Range for {path}")
    count_value = content_range.rsplit("/", 1)[1]
    if count_value == "*":
        raise RuntimeError(f"PostgREST exact count unavailable for {path}")
    return int(count_value)


def postgrest_get(path: str) -> Any:
    """Read a public-schema PostgREST path."""
    return _postgrest_request(path)


def postgrest_rpc(function_name: str, payload: dict[str, Any]) -> Any:
    """Call a public PostgREST RPC."""
    return _postgrest_request(f"rpc/{function_name}", method="POST", payload=payload)


def _eq(value: str | int) -> str:
    return urlparse.quote(str(value), safe="")


def _first(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not rows:
        raise RuntimeError(f"No Supabase rows returned for {label}")
    return rows[0]


def fetch_slice_inputs(
    *,
    cbsa_code: str,
    naics_code: str,
    niche_normalized: str,
    year: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], int, dict[str, Any] | None]:
    """Fetch source rows for one NAICS/year/CBSA slice-lite cell."""
    metro = _first(
        postgrest_get(
            "metros"
            f"?cbsa_code=eq.{_eq(cbsa_code)}"
            "&select=cbsa_code,cbsa_name,population,households,owner_occupancy_rate,"
            "median_household_income_usd,acs_vintage,population_class"
        ),
        "metro",
    )
    cbp = _first(
        postgrest_get(
            "census_cbp_establishments"
            f"?cbsa_code=eq.{_eq(cbsa_code)}"
            f"&naics_code=eq.{_eq(naics_code)}"
            f"&year=eq.{year}"
            "&select=*"
        ),
        "census_cbp_establishments",
    )
    seo_rows = postgrest_get(
        "seo_facts"
        f"?cbsa_code=eq.{_eq(cbsa_code)}"
        f"&niche_normalized=eq.{_eq(niche_normalized)}"
        "&intent=in.(transactional,commercial)"
        "&select=*"
    )
    if not seo_rows:
        raise RuntimeError("No Supabase rows returned for seo_facts")

    peer_count = postgrest_count(
        "census_cbp_establishments"
        f"?naics_code=eq.{_eq(naics_code)}"
        f"&year=eq.{year}"
        "&est=gt.50"
        "&suppressed=eq.false"
        "&metros.population=gt.100000"
        "&select=cbsa_code,metros!inner(population)"
    )
    benchmark = None
    population_class = metro.get("population_class")
    if population_class:
        benchmark_rows = postgrest_get(
            "seo_benchmarks"
            f"?niche_normalized=eq.{_eq(niche_normalized)}"
            f"&population_class=eq.{_eq(population_class)}"
            "&select=*"
        )
        benchmark = benchmark_rows[0] if benchmark_rows else None

    return metro, cbp, build_seo_rollup(seo_rows), peer_count, benchmark


def persist_cell_record(record: dict[str, Any]) -> Any:
    """Persist through public RPC so the sonar schema need not be REST-exposed."""
    return postgrest_rpc("persist_sonar_slice_lite", {"p_record": record})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Build a deterministic Sonar slice-lite CellRecord.",
    )
    parser.add_argument("--naics-code", default=DEFAULT_NAICS_CODE)
    parser.add_argument("--cbsa-code", default=DEFAULT_CBSA_CODE)
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--niche-normalized", default=DEFAULT_NICHE_NORMALIZED)
    parser.add_argument("--persist", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        metro, cbp, seo, peer_count, benchmark = fetch_slice_inputs(
            cbsa_code=args.cbsa_code,
            naics_code=args.naics_code,
            niche_normalized=args.niche_normalized,
            year=args.year,
        )
        record = build_cell_record(
            metro=metro,
            cbp=cbp,
            seo=seo,
            peer_count=peer_count,
            benchmark=benchmark,
            year=args.year,
            naics_code=args.naics_code,
        )
        print(json.dumps(record, indent=2, sort_keys=True))
        if args.persist:
            persist_result = persist_cell_record(record)
            if not persist_result:
                raise RuntimeError("persist_sonar_slice_lite returned an empty response")
            print(f"persisted: {json.dumps(persist_result, sort_keys=True)}", file=sys.stderr)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    except (urlerror.HTTPError, urlerror.URLError, TimeoutError, OSError) as exc:
        print(f"network error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
