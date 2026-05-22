import pytest

from scripts.benchmarks import recompute_benchmarks


def test_parse_args_accepts_expected_project_ref() -> None:
    args = recompute_benchmarks.parse_args(
        ["30", "--expected-project-ref", "wuybidpvqhhgkukpyyhq"]
    )

    assert args.window_days == 30
    assert args.expected_project_ref == "wuybidpvqhhgkukpyyhq"


def test_expected_project_ref_guard_accepts_matching_url(monkeypatch) -> None:
    monkeypatch.setattr(
        recompute_benchmarks,
        "SUPABASE_URL",
        "https://wuybidpvqhhgkukpyyhq.supabase.co",
    )

    recompute_benchmarks.validate_expected_project_ref("wuybidpvqhhgkukpyyhq")


def test_expected_project_ref_guard_rejects_mismatched_url(monkeypatch) -> None:
    monkeypatch.setattr(
        recompute_benchmarks,
        "SUPABASE_URL",
        "https://wuybidpvqhhgkukpyyhq.supabase.co",
    )

    with pytest.raises(RuntimeError, match="expected eoajvifhbmqmoluiokcj"):
        recompute_benchmarks.validate_expected_project_ref("eoajvifhbmqmoluiokcj")


def test_expected_project_ref_guard_rejects_suffixed_supabase_host(monkeypatch) -> None:
    monkeypatch.setattr(
        recompute_benchmarks,
        "SUPABASE_URL",
        "https://wuybidpvqhhgkukpyyhq.supabase.co.evil.test",
    )

    with pytest.raises(RuntimeError, match="expected wuybidpvqhhgkukpyyhq, got <unknown>"):
        recompute_benchmarks.validate_expected_project_ref("wuybidpvqhhgkukpyyhq")


def test_main_validates_project_ref_before_rpc(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        recompute_benchmarks,
        "SUPABASE_URL",
        "https://wuybidpvqhhgkukpyyhq.supabase.co",
    )

    def fail_rpc(*_args, **_kwargs):  # noqa: ANN001
        raise AssertionError("rpc should not run after project mismatch")

    monkeypatch.setattr(recompute_benchmarks, "rpc", fail_rpc)

    with pytest.raises(SystemExit) as exc:
        recompute_benchmarks.main(["--expected-project-ref", "eoajvifhbmqmoluiokcj"])

    assert exc.value.code == 2
    assert "Supabase project ref mismatch" in capsys.readouterr().err
