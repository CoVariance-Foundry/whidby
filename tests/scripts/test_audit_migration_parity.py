import json

from scripts.supabase.audit_migration_parity import classify_migrations, main


def test_classify_migrations_detects_missing_required_names():
    local = [
        "001_core_schema",
        "014_user_management_billing",
        "015_explore_refresh_control",
        "016_consumer_onboarding",
        "017_strategy_discovery_system",
        "018_internal_user_entitlements",
    ]
    remote = [
        {"version": "001", "name": "core_schema"},
        {"version": "20260421231306", "name": "001_core_schema"},
    ]

    result = classify_migrations(local, remote)

    assert result["missing_names"] == [
        "014_user_management_billing",
        "015_explore_refresh_control",
        "016_consumer_onboarding",
        "017_strategy_discovery_system",
        "018_internal_user_entitlements",
    ]
    assert result["present_names"] == ["001_core_schema"]


def test_classify_migrations_accepts_timestamped_remote_equivalents():
    local = ["009_metros_and_census", "010_v2_benchmarks"]
    remote = [
        {"version": "20260426205328", "name": "metros_and_census"},
        {"version": "20260517191229", "name": "v2_benchmarks_schema_only"},
    ]

    result = classify_migrations(local, remote)

    assert result["missing_names"] == []
    assert result["present_names"] == [
        "009_metros_and_census",
        "010_v2_benchmarks",
    ]


def test_cli_missing_migrations_exits_1(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_core_schema.sql").write_text("-- migration\n")
    (migrations_dir / "014_user_management_billing.sql").write_text("-- migration\n")
    remote_json = tmp_path / "remote.json"
    remote_json.write_text(json.dumps([{"version": "001", "name": "core_schema"}]))
    monkeypatch.setattr(
        "sys.argv",
        [
            "audit_migration_parity.py",
            "--migrations-dir",
            str(migrations_dir),
            "--remote-json",
            str(remote_json),
        ],
    )

    assert main() == 1


def test_cli_full_parity_exits_0(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_core_schema.sql").write_text("-- migration\n")
    (migrations_dir / "010_v2_benchmarks.sql").write_text("-- migration\n")
    remote_json = tmp_path / "remote.json"
    remote_json.write_text(
        json.dumps(
            {
                "migrations": [
                    {"version": "001", "name": "core_schema"},
                    {"version": "20260517191229", "name": "v2_benchmarks_schema_only"},
                ]
            }
        )
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "audit_migration_parity.py",
            "--migrations-dir",
            str(migrations_dir),
            "--remote-json",
            str(remote_json),
        ],
    )

    assert main() == 0


def test_cli_missing_migrations_dir_exits_nonzero(tmp_path, monkeypatch):
    remote_json = tmp_path / "remote.json"
    remote_json.write_text(json.dumps([]))
    monkeypatch.setattr(
        "sys.argv",
        [
            "audit_migration_parity.py",
            "--migrations-dir",
            str(tmp_path / "missing"),
            "--remote-json",
            str(remote_json),
        ],
    )

    assert main() == 1


def test_cli_empty_migrations_dir_exits_nonzero(tmp_path, monkeypatch):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    remote_json = tmp_path / "remote.json"
    remote_json.write_text(json.dumps([]))
    monkeypatch.setattr(
        "sys.argv",
        [
            "audit_migration_parity.py",
            "--migrations-dir",
            str(migrations_dir),
            "--remote-json",
            str(remote_json),
        ],
    )

    assert main() == 1


def test_cli_suffix_with_wrong_remote_version_exits_nonzero(
    tmp_path,
    monkeypatch,
    capsys,
):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_core_schema.sql").write_text("-- migration\n")
    remote_json = tmp_path / "remote.json"
    remote_json.write_text(json.dumps([{"version": "999", "name": "core_schema"}]))
    monkeypatch.setattr(
        "sys.argv",
        [
            "audit_migration_parity.py",
            "--migrations-dir",
            str(migrations_dir),
            "--remote-json",
            str(remote_json),
        ],
    )

    assert main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["missing_names"] == ["001_core_schema"]
    assert result["present_names"] == []
