"""Crash evidence must never include unrelated host or simulator reports."""

import json
import os
from pathlib import Path
from time import time

from uiautomation.utils.crash_reports import collect_simulator_crashes

UDID = "00000000-0000-0000-0000-000000000001"


def test_crash_capture_filters_app_simulator_and_time(tmp_path: Path) -> None:
    simulator = tmp_path / "Library/Developer/CoreSimulator/Devices" / UDID
    simulator.mkdir(parents=True)
    reports = tmp_path / "Library/Logs/DiagnosticReports"
    reports.mkdir(parents=True)
    output = tmp_path / "output"
    output.mkdir()
    start = time() - 60
    for name, bundle, coalition in [
        ("match", "com.apple.mobilecal", f"com.apple.CoreSimulator.SimDevice.{UDID}"),
        ("other-app", "com.apple.Maps", f"com.apple.CoreSimulator.SimDevice.{UDID}"),
        ("host", "com.apple.mobilecal", "host"),
        ("old", "com.apple.mobilecal", f"com.apple.CoreSimulator.SimDevice.{UDID}"),
        ("other-simulator", "com.apple.mobilecal", "com.apple.CoreSimulator.SimDevice.other"),
    ]:
        path = reports / f"{name}.ips"
        path.write_text(
            json.dumps({"bundleID": bundle}) + "\n" + json.dumps({"coalitionName": coalition})
        )
        if name == "old":
            os.utime(path, (start - 1, start - 1))
    assert collect_simulator_crashes(output, UDID, "com.apple.mobilecal", start, tmp_path) == []
    assert len(list(output.glob("*.ips"))) == 1
    assert (output / "crash-1.ips").read_text() == (reports / "match.ips").read_text()


def test_simulator_local_reports_need_no_host_identity_and_are_bounded(tmp_path: Path) -> None:
    reports = (
        tmp_path
        / "Library/Developer/CoreSimulator/Devices"
        / UDID
        / "data/Library/Logs/CrashReporter"
    )
    reports.mkdir(parents=True)
    output = tmp_path / "output"
    output.mkdir()
    for index in range(8):
        (reports / f"{index}.ips").write_text(json.dumps({"bundleID": "com.apple.mobilecal"}))
    collect_simulator_crashes(output, UDID, "com.apple.mobilecal", time() - 60, tmp_path)
    assert len(list(output.glob("*.ips"))) == 5


def test_malformed_report_does_not_block_other_evidence(tmp_path: Path) -> None:
    reports = (
        tmp_path
        / "Library/Developer/CoreSimulator/Devices"
        / UDID
        / "data/Library/Logs/CrashReporter"
    )
    reports.mkdir(parents=True)
    (reports / "bad.ips").write_text("not JSON")
    assert collect_simulator_crashes(tmp_path, UDID, "com.apple.mobilecal", time() - 60, tmp_path)
