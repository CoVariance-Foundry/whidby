from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EQUIVALENT_REMOTE_NAMES: dict[str, tuple[str, ...]] = {
    "006_authenticated_delete_reports": ("authenticated_delete_reports",),
    "009_metros_and_census": (
        "metros_and_census",
        "009_explore_metros_table_bootstrap",
    ),
    "010_v2_benchmarks": (
        "v2_benchmarks",
        "v2_benchmarks_schema_only",
        "010_backfill_metros_from_existing_reports",
    ),
    "011_data_provider_tables": ("data_provider_tables",),
    "012_recompute_seo_benchmarks": ("recompute_seo_benchmarks",),
    "013_sonar_slice_lite": (
        "sonar_slice_lite",
        "fix_sonar_slice_lite_rpc_conflict",
    ),
}


def local_migration_names(migrations_dir: Path) -> list[str]:
    if not migrations_dir.is_dir():
        raise ValueError(f"migrations directory not found: {migrations_dir}")

    migration_names = sorted(
        path.stem
        for path in migrations_dir.glob("*.sql")
        if path.name[:1].isdigit()
    )
    if not migration_names:
        raise ValueError(f"no local migration files found: {migrations_dir}")

    return migration_names


def _remote_name_set(remote: list[dict[str, Any]]) -> set[str]:
    return {
        migration["name"]
        for migration in remote
        if isinstance(migration.get("name"), str)
    }


def _remote_records(remote: list[dict[str, Any]]) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    for migration in remote:
        name = migration.get("name")
        if isinstance(name, str):
            records.append((name, str(migration.get("version", ""))))
    return records


def _local_version(local_name: str) -> str:
    return local_name.split("_", maxsplit=1)[0]


def _is_present(
    local_name: str,
    remote_names: set[str],
    remote_records: list[tuple[str, str]],
) -> bool:
    suffix = local_name.split("_", maxsplit=1)[1] if "_" in local_name else local_name
    equivalent_names = EQUIVALENT_REMOTE_NAMES.get(local_name, ())

    return (
        local_name in remote_names
        or any(
            remote_name == suffix and remote_version == _local_version(local_name)
            for remote_name, remote_version in remote_records
        )
        or any(name in remote_names for name in equivalent_names)
    )


def classify_migrations(
    local: list[str],
    remote: list[dict[str, Any]],
) -> dict[str, list[str]]:
    remote_names = _remote_name_set(remote)
    remote_records = _remote_records(remote)
    present_names: list[str] = []
    missing_names: list[str] = []

    for local_name in local:
        if _is_present(local_name, remote_names, remote_records):
            present_names.append(local_name)
        else:
            missing_names.append(local_name)

    return {
        "present_names": present_names,
        "missing_names": missing_names,
    }


def _remote_migrations(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("migrations"), list):
        return [
            item
            for item in payload["migrations"]
            if isinstance(item, dict)
        ]
    raise ValueError("remote JSON must be a list or object with a migrations list")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare local Supabase migration names to remote history.",
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=Path("supabase/migrations"),
    )
    parser.add_argument("--remote-json", type=Path, required=True)
    args = parser.parse_args()

    try:
        local_names = local_migration_names(args.migrations_dir)
        payload = json.loads(args.remote_json.read_text())
        remote_migrations = _remote_migrations(payload)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, indent=2, sort_keys=True))
        return 1

    result = classify_migrations(
        local_names,
        remote_migrations,
    )

    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["missing_names"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
