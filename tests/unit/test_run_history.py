"""Run history separates targets and counts teardown failures once."""

import json
from pathlib import Path

import pytest

from uiautomation.cli import main
from uiautomation.utils.run_history import flaky_tests, summarize_history


def write_run(
    root: Path, run_id: str, runtime: str = "27.0", failed: bool = False, **extra
) -> None:
    directory = root / run_id
    directory.mkdir()
    manifest = {
        "run_id": run_id,
        "finished_at": "done",
        "worker": None,
        "target": {"kind": "simulator", "device_name": "Test iPhone", "platform_version": runtime},
        "results": [
            {"nodeid": "test_one", "phase": "setup", "outcome": "passed", "duration_seconds": 2},
            {"nodeid": "test_one", "phase": "call", "outcome": "passed", "duration_seconds": 3},
            {
                "nodeid": "test_one",
                "phase": "teardown",
                "outcome": "failed" if failed else "passed",
                "duration_seconds": 1,
            },
        ],
        **extra,
    }
    (directory / "run.json").write_text(json.dumps(manifest))


def test_history_groups_targets_and_excludes_workers_and_partial_runs(tmp_path: Path) -> None:
    write_run(tmp_path, "one")
    write_run(tmp_path, "two", failed=True)
    write_run(tmp_path, "new-runtime", runtime="28.0")
    write_run(tmp_path, "worker", worker="gw0")
    write_run(tmp_path, "partial", finished_at=None)
    report = summarize_history(tmp_path)
    assert report["completed_runs"] == 3
    assert report["ignored_manifests"] == 2
    assert len(report["tests"]) == 2
    row = report["tests"][0]
    assert (row["failed"], row["passed"], row["runs"]) == (1, 1, 2)
    assert row["mixed_outcomes"] is True
    assert row["median_seconds"] == 6
    assert row["median_setup_seconds"] == 2


def test_history_ignores_malformed_reports_and_cli_outputs_json(tmp_path: Path, capsys) -> None:
    write_run(tmp_path, "valid")
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "run.json").write_text("broken")
    assert main(["history", "--artifacts-dir", str(tmp_path), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["completed_runs"] == 1
    assert output["ignored_manifests"] == 1


def _write_series(root: Path, outcomes: str) -> None:
    """Write one run per letter (P/F), finishing in order regardless of directory names."""
    for index, outcome in enumerate(outcomes):
        write_run(
            root,
            f"z{len(outcomes) - index}",
            failed=outcome == "F",
            finished_at=f"2026-10-30T10:00:{index:02d}+00:00",
        )


def test_history_orders_outcomes_by_finish_time_and_rates_failures(tmp_path: Path) -> None:
    _write_series(tmp_path, "PPFPF")
    row = summarize_history(tmp_path)["tests"][0]
    assert row["outcomes"] == "PPFPF"
    assert row["fail_rate"] == 0.4


def test_history_window_keeps_only_most_recent_runs(tmp_path: Path) -> None:
    _write_series(tmp_path, "FFPPP")
    report = summarize_history(tmp_path, last_runs=3)
    assert report["completed_runs"] == 3
    row = report["tests"][0]
    assert (row["outcomes"], row["mixed_outcomes"]) == ("PPP", False)


def test_skips_are_excluded_from_fail_rate(tmp_path: Path) -> None:
    write_run(tmp_path, "skipped")
    manifest = tmp_path / "skipped" / "run.json"
    run = json.loads(manifest.read_text())
    for result in run["results"]:
        result["outcome"] = "skipped" if result["phase"] == "call" else "passed"
    manifest.write_text(json.dumps(run))
    row = summarize_history(tmp_path)["tests"][0]
    assert (row["outcomes"], row["fail_rate"]) == ("S", None)


def test_cli_flaky_lists_only_mixed_tests(tmp_path: Path, capsys) -> None:
    _write_series(tmp_path, "PFP")
    write_run(tmp_path, "steady", runtime="28.0", finished_at="2026-10-30T11:00:00+00:00")
    assert main(["history", "--artifacts-dir", str(tmp_path), "--flaky"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2
    assert "1/3 failed (33%) PFP (2 flips)" in lines[1]
    assert "27.0" in lines[1]

    assert main(["history", "--artifacts-dir", str(tmp_path), "--flaky", "--json"]) == 0
    tests = json.loads(capsys.readouterr().out)["tests"]
    assert [row["runtime"] for row in tests] == ["27.0"]


def test_cli_flaky_reports_when_nothing_is_flaky(tmp_path: Path, capsys) -> None:
    write_run(tmp_path, "steady")
    assert main(["history", "--artifacts-dir", str(tmp_path), "--flaky"]) == 0
    assert "No test both passed and failed" in capsys.readouterr().out


def test_cli_rejects_non_positive_run_window(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["history", "--artifacts-dir", str(tmp_path), "--runs", "0"])


def test_flaky_view_ranks_alternating_tests_above_fixed_regressions(tmp_path: Path) -> None:
    """A test that failed then stayed fixed is less flaky than one that keeps flipping."""
    for index, (regression, flaky) in enumerate(zip("FFFFPPPP", "PFPPFPPP", strict=True)):
        directory = tmp_path / f"run{index}"
        directory.mkdir()
        results = [
            {"nodeid": nodeid, "phase": "call", "outcome": outcome, "duration_seconds": 1}
            for nodeid, outcome in (
                ("regression", "failed" if regression == "F" else "passed"),
                ("flaky", "failed" if flaky == "F" else "passed"),
            )
        ]
        (directory / "run.json").write_text(
            json.dumps(
                {
                    "run_id": f"run{index}",
                    "finished_at": f"2026-10-30T10:00:{index:02d}+00:00",
                    "target": {"kind": "simulator"},
                    "results": results,
                }
            )
        )
    rows = flaky_tests(summarize_history(tmp_path))
    assert [(row["nodeid"], row["flips"]) for row in rows] == [("flaky", 4), ("regression", 1)]
