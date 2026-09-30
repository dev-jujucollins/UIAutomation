"""Run history separates targets and counts teardown failures once."""

import json
from pathlib import Path

from uiautomation.cli import main
from uiautomation.utils.run_history import summarize_history


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
