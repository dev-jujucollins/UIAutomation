"""`uiautomation devices` shows the run target and why it was chosen."""

import json
from unittest.mock import patch

from uiautomation import cli
from uiautomation.utils.simulator_control import SimulatorDevice

DEVICES = [
    SimulatorDevice("iPhone Air", "air", "27.2", "Booted", True),
    SimulatorDevice("iPhone 18 Pro", "pro", "27.2", "Shutdown", True),
    SimulatorDevice("iPhone 17 Pro", "old", "26.4", "Shutdown", True),
    SimulatorDevice("iPhone Broken", "gone", "27.2", "Shutdown", False),
]


def _run(*args: str) -> int:
    with patch.object(cli, "list_available_simulators", return_value=DEVICES):
        return cli.main(["devices", *args])


def test_text_marks_target_groups_newest_runtime_first(capsys) -> None:
    assert _run() == 0
    out = capsys.readouterr().out
    assert out.startswith("Default target: iPhone 18 Pro (iOS 27.2) pro\n  Why: highest-ranked")
    lines = out.splitlines()
    assert lines.index("iOS 27.2") < lines.index("iOS 26.4")
    assert "  → iPhone 18 Pro" in out and "    iPhone Air" in out
    assert "iPhone Broken" not in out


def test_overrides_select_the_named_device(capsys) -> None:
    assert _run("--device-name", "iPhone Air") == 0
    assert "Why: matches --device-name; newest matching runtime" in capsys.readouterr().out


def test_json_reports_target_reason_and_devices(capsys) -> None:
    assert _run("--json") == 0
    report = json.loads(capsys.readouterr().out)
    assert report["target"]["udid"] == "pro"
    assert report["reason"].startswith("highest-ranked")
    assert [device["udid"] for device in report["devices"]] == ["air", "pro", "old"]


def test_no_match_lists_devices_and_fails(capsys) -> None:
    assert _run("--platform-version", "99.0") == 1
    out = capsys.readouterr().out
    assert out.startswith("No target: No available simulator matches")
    assert "  → " not in out and "iPhone Air" in out
