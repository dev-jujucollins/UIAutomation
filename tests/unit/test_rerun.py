"""`uiautomation rerun` repeats the latest run's failures on the same target."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from uiautomation import cli
from uiautomation.utils.run_history import failed_tests, latest_run, rerun_options

FAILED_CALL = "tests/integration/test_maps.py::test_route[allow]"
FAILED_TEARDOWN = "tests/integration/test_calendar.py::test_editor"


def _result(nodeid: str, phase: str, outcome: str) -> dict:
    return {"nodeid": nodeid, "phase": phase, "outcome": outcome, "duration_seconds": 1}


def _manifest(run_id: str, finished_at: str | None, **extra) -> dict:
    return {
        "run_id": run_id,
        "finished_at": finished_at,
        "worker": None,
        "target": {"kind": "simulator", "device_name": "iPhone 18 Pro", "platform_version": "27.2"},
        "options": {
            "run_integration": True,
            "run_lifecycle": False,
            "headless_simulator": True,
            "timeout": 300,
            "numprocesses": 4,
        },
        "results": [
            _result("tests/unit/test_ok.py::test_ok", "call", "passed"),
            _result(FAILED_CALL, "call", "failed"),
            _result(FAILED_CALL, "teardown", "passed"),
            _result(FAILED_TEARDOWN, "call", "passed"),
            _result(FAILED_TEARDOWN, "teardown", "failed"),
        ],
        **extra,
    }


def _write(root: Path, manifest: dict) -> None:
    directory = root / f"local-{manifest['run_id']}" / manifest["run_id"]
    directory.mkdir(parents=True)
    (directory / "run.json").write_text(json.dumps(manifest))


def test_latest_run_is_newest_finished_controller(tmp_path: Path) -> None:
    _write(tmp_path, _manifest("old", "2026-10-30T09:00:00+00:00"))
    _write(tmp_path, _manifest("new", "2026-10-30T10:00:00+00:00"))
    _write(tmp_path, _manifest("unfinished", None))
    _write(tmp_path, _manifest("worker", "2026-10-30T11:00:00+00:00", worker="gw0"))
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "run.json").write_text("not json")
    run = latest_run(tmp_path)
    assert run is not None and run["run_id"] == "new"


def test_failures_in_any_phase_are_listed_once_in_run_order() -> None:
    assert failed_tests(_manifest("run", "done")) == [FAILED_CALL, FAILED_TEARDOWN]


def test_options_restore_target_and_flags_but_stay_serial() -> None:
    assert rerun_options(_manifest("run", "done")) == [
        "--run-integration",
        "--headless-simulator",
        "--timeout",
        "300",
        "--device-name",
        "iPhone 18 Pro",
        "--platform-version",
        "27.2",
    ]


def test_explicit_options_replace_recorded_ones() -> None:
    options = rerun_options(_manifest("run", "done"), skip={"--timeout", "--device-name"})
    assert "--timeout" not in options and "--device-name" not in options
    assert ["--platform-version", "27.2"] == options[-2:]


def test_physical_target_does_not_reuse_device_identity() -> None:
    run = _manifest("run", "done", target={"kind": "physical", "device_name": "Phone"})
    assert "--device-name" not in rerun_options(run)


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock(return_value=0)
    monkeypatch.setattr(cli, "run_suite", mock)
    return mock


def test_cli_reruns_failures_with_recorded_and_explicit_options(
    tmp_path: Path, runner: MagicMock, capsys
) -> None:
    _write(tmp_path, _manifest("last", "2026-10-30T10:00:00+00:00"))
    assert cli.main(["rerun", "--artifacts-dir", str(tmp_path), "--timeout", "600"]) == 0
    suite, options, artifacts = runner.call_args.args[:3]
    assert suite == "rerun" and artifacts == tmp_path
    assert runner.call_args.kwargs["selection"] == [FAILED_CALL, FAILED_TEARDOWN]
    assert options[-2:] == ["--timeout", "600"]
    assert options.count("--timeout") == 1
    assert "Rerunning 2 failed test(s) from run last" in capsys.readouterr().out


def test_cli_reports_clean_run_without_running(tmp_path: Path, runner: MagicMock, capsys) -> None:
    clean = _manifest("clean", "done")
    clean["results"] = [_result("tests/unit/test_ok.py::test_ok", "call", "passed")]
    _write(tmp_path, clean)
    assert cli.main(["rerun", "--artifacts-dir", str(tmp_path)]) == 0
    runner.assert_not_called()
    assert "no failures" in capsys.readouterr().out


def test_cli_without_runs_fails(tmp_path: Path, runner: MagicMock) -> None:
    assert cli.main(["rerun", "--artifacts-dir", str(tmp_path)]) == 1
    runner.assert_not_called()


def test_cli_requires_udid_again_for_physical_runs(tmp_path: Path, runner: MagicMock) -> None:
    _write(tmp_path, _manifest("phone", "done", target={"kind": "physical"}))
    with pytest.raises(SystemExit):
        cli.main(["rerun", "--artifacts-dir", str(tmp_path)])
    runner.assert_not_called()
    assert (
        cli.main(["rerun", "--artifacts-dir", str(tmp_path), "--udid", "U", "--team-id", "T"]) == 0
    )
