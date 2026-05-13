"""Run and audit seo_benchmarks recomputation.

This script uses Supabase PostgREST RPC, so it requires service-role credentials.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib import error as urlerror
from urllib import request as urlreq


SUPABASE_URL = os.environ.get(
    "BENCHMARK_SUPABASE_URL",
    "https://wuybidpvqhhgkukpyyhq.supabase.co",
)
SUPABASE_KEY = (
    os.environ.get("BENCHMARK_SUPABASE_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)


def positive_int(value: str) -> int:
    """Parse a positive integer argparse value."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")

    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Recompute Supabase seo_benchmarks for a recent fact window.",
    )
    parser.add_argument(
        "window_days",
        nargs="?",
        default=120,
        type=positive_int,
        help="Positive day window for recent seo_facts. Defaults to 120.",
    )
    return parser.parse_args(argv)


def network_error_body(exc: urlerror.URLError | TimeoutError | OSError) -> str:
    """Format transport errors without surfacing a traceback."""
    reason = getattr(exc, "reason", None)
    detail = str(reason) if reason is not None else str(exc)
    return f"error={exc.__class__.__name__}: {detail}"


def rpc(function_name: str, payload: dict[str, int]) -> tuple[int, str]:
    """Call a Supabase PostgREST RPC and return status plus response body."""
    if not SUPABASE_KEY:
        raise RuntimeError("BENCHMARK_SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY is required")

    req = urlreq.Request(
        f"{SUPABASE_URL}/rest/v1/rpc/{function_name}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlreq.urlopen(req, timeout=120) as response:
            return response.status, response.read().decode()
    except urlerror.HTTPError as exc:
        return exc.code, exc.read().decode()
    except (urlerror.URLError, TimeoutError, OSError) as exc:
        return 0, network_error_body(exc)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    window_days = args.window_days
    try:
        status, body = rpc("recompute_seo_benchmarks", {"p_window_days": window_days})
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    print(f"status={status}")
    print(body)
    if status < 200 or status >= 300:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
