"""Xcode result bundles become run manifests the rest of the tooling can read."""

import json
from pathlib import Path

from swift_samples import SUMMARY, TESTS

from uiautomation.utils.run_history import latest_run, summarize_history
from uiautomation.utils.xcresult import (
    build_manifest,
    flatten_tests,
    screenshots_from_manifest,
)


def _manifest(run_id: str = "run-1") -> dict:
    return build_manifest(
        SUMMARY,
        flatten_tests(TESTS),
        run_id=run_id,
        exit_status=1,
        options={"run_lifecycle": False},
        environment={"commit": "abc"},
    )


def test_flatten_reads_every_case_with_its_suite_outcome_and_notes() -> None:
    tests = {test.name: test for test in flatten_tests(TESTS)}
    assert set(tests) == {
        "testContactCreateReopenEditDelete",
        "testNavigateToGeneral",
        "testSettingsAppLaunches",
    }
    failed = tests["testNavigateToGeneral"]
    assert (failed.suite, failed.outcome) == ("SettingsTests", "failed")
    assert failed.location == "SettingsTests.swift:30"
    assert failed.identifier == "SettingsTests/testNavigateToGeneral()"
    assert failed.nodeid == "swift::SettingsTests/testNavigateToGeneral"
    skipped = tests["testContactCreateReopenEditDelete"]
    assert skipped.outcome == "skipped"
    assert skipped.messages[0].endswith("UIAUTOMATION_RUN_LIFECYCLE=1")
    assert tests["testSettingsAppLaunches"].messages == ()


def test_unknown_or_missing_result_is_never_reported_as_passed() -> None:
    odd = {
        "testNodes": [
            {
                "nodeType": "Test Suite",
                "name": "OddTests",
                "children": [
                    {"nodeType": "Test Case", "name": "testNew()", "result": "Something New"},
                    {"nodeType": "Test Case", "name": "testNone()"},
                    {
                        "nodeType": "Test Case",
                        "name": "testExpected()",
                        "result": "Expected Failure",
                    },
                ],
            }
        ]
    }
    outcomes = {test.name: test.outcome for test in flatten_tests(odd)}
    assert outcomes == {"testNew": "failed", "testNone": "failed", "testExpected": "passed"}


def test_manifest_matches_the_pytest_shape() -> None:
    manifest = _manifest()
    assert manifest["runner"] == "xcuitest"
    assert manifest["target"] == {
        "kind": "simulator",
        "device_name": "iPhone 18 Pro",
        "platform_version": "27.2",
        "model": "iPhone 18 Pro",
    }
    assert manifest["summary"] == {"skipped": 1, "failed": 1, "passed": 1}
    assert manifest["duration_seconds"] == 140.675
    assert manifest["started_at"].startswith("2026-11-10T")
    assert {result["phase"] for result in manifest["results"]} == {"call"}


def test_history_reads_swift_runs_but_rerun_passes_over_them(tmp_path: Path) -> None:
    (tmp_path / "swift").mkdir()
    (tmp_path / "swift" / "run.json").write_text(json.dumps(_manifest()))
    history = summarize_history(tmp_path)
    assert (history["completed_runs"], history["ignored_manifests"]) == (1, 0)
    row = next(row for row in history["tests"] if row["failed"])
    assert row["nodeid"] == "swift::SettingsTests/testNavigateToGeneral"
    assert (row["kind"], row["device"], row["runtime"]) == ("simulator", "iPhone 18 Pro", "27.2")
    # rerun drives pytest, so the newest Swift run must not become its input.
    assert latest_run(tmp_path) is None
    pytest_run = {
        "run_id": "py",
        "finished_at": "2020-01-01T00:00:00+00:00",
        "worker": None,
        "results": [],
    }
    (tmp_path / "py").mkdir()
    (tmp_path / "py" / "run.json").write_text(json.dumps(pytest_run))
    assert latest_run(tmp_path)["run_id"] == "py"


def test_screenshots_come_only_from_named_attachments_inside_the_export(tmp_path: Path) -> None:
    (tmp_path / "shot.jpeg").write_bytes(b"jpeg")
    (tmp_path / "video.mp4").write_bytes(b"mp4")
    outside = tmp_path.parent / "outside.jpeg"
    outside.write_bytes(b"secret")
    manifest = [
        {
            "testIdentifier": "SettingsTests/testNavigateToGeneral()",
            "attachments": [
                {
                    "exportedFileName": "video.mp4",
                    "suggestedHumanReadableName": "Screen Recording.mp4",
                },
                {
                    "exportedFileName": "shot.jpeg",
                    "suggestedHumanReadableName": "Failure screenshot_0_ABC.jpeg",
                },
            ],
        },
        {
            "testIdentifier": "MapsTests/testEscape()",
            "attachments": [
                {
                    "exportedFileName": "../outside.jpeg",
                    "suggestedHumanReadableName": "Failure screenshot_0_DEF.jpeg",
                },
                {
                    "exportedFileName": "missing.jpeg",
                    "suggestedHumanReadableName": "Failure screenshot_1.jpeg",
                },
            ],
        },
        "not an entry",
    ]
    assert screenshots_from_manifest(manifest, tmp_path) == {
        "SettingsTests/testNavigateToGeneral()": tmp_path / "shot.jpeg"
    }
    assert screenshots_from_manifest({"unexpected": True}, tmp_path) == {}
