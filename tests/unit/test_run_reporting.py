"""Run reports preserve results while excluding credentials and device IDs."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from uiautomation.utils import run_reporting
from uiautomation.utils.run_reporting import RunReport, collect_environment, sanitized_capabilities


def test_capabilities_use_allowlist_at_every_supported_level() -> None:
    """Unknown fields, secrets, URLs, signing teams and UDIDs must not leak."""
    capabilities = {
        "platformName": "iOS",
        "appium:platformVersion": "27.0",
        "appium:deviceName": "Test iPhone",
        "appium:udid": "secret-device",
        "appium:xcodeOrgId": "secret-team",
        "accessKey": "secret-key",
        "server": "https://user:password@example.test",
        "customProvider": {"token": "secret-token"},
        "appium:options": {"noReset": False, "password": "secret-password", "udid": "secret-id"},
        "language": {"unexpected": "secret-object"},
    }
    sanitized = sanitized_capabilities(capabilities)
    assert sanitized == {
        "platformName": "iOS",
        "appium:platformVersion": "27.0",
        "appium:deviceName": "Test iPhone",
        "appium:options": {"noReset": False},
    }
    assert "secret" not in json.dumps(sanitized)


def test_unit_metadata_does_not_probe_native_tools(tmp_path: Path, monkeypatch) -> None:
    """Device-free runs can record provenance on Linux with no Appium/Xcode."""
    probe = Mock(return_value="revision")
    monkeypatch.setattr(run_reporting, "_command_output", probe)
    metadata = collect_environment(tmp_path, integration=False)
    probe.assert_called_once_with(["git", "rev-parse", "HEAD"], tmp_path)
    assert metadata["commit"] == "revision"
    assert metadata["python"]
    assert metadata["packages"]["pytest"]
    assert metadata["tools"] == {}


@pytest.mark.parametrize("driver_json", ['{"xcuitest":{"version":"9.1.0"}}', "broken", "[]"])
def test_native_metadata_handles_driver_output(
    tmp_path: Path, monkeypatch, driver_json: str
) -> None:
    """A malformed driver listing must not prevent running tests."""
    probe = Mock(side_effect=["Xcode 27.0", "3.0.0", driver_json, "revision"])
    monkeypatch.setattr(run_reporting, "_command_output", probe)
    metadata = collect_environment(tmp_path, integration=True)
    assert metadata["tools"]["xcode"] == "Xcode 27.0"
    assert metadata["tools"]["xcuitest"] == ("9.1.0" if driver_json.startswith("{") else None)


@pytest.mark.parametrize("error", [FileNotFoundError(), subprocess.TimeoutExpired("probe", 10)])
def test_unavailable_probe_is_bounded_and_optional(tmp_path: Path, monkeypatch, error) -> None:
    """Absent tools and timeouts are reported as unavailable."""
    run = Mock(side_effect=error)
    monkeypatch.setattr(run_reporting.subprocess, "run", run)
    assert run_reporting._command_output(["appium", "--version"], tmp_path) is None
    assert run.call_args.kwargs["timeout"] == 10


def test_manifest_preserves_teardown_failures_and_actual_target(
    tmp_path: Path, monkeypatch
) -> None:
    """Each test contributes one result, even with multiple pytest phases."""
    monkeypatch.setattr(run_reporting, "collect_environment", lambda *_: {"commit": "revision"})
    report = RunReport(tmp_path / "run-id", tmp_path, False, {"kind": "simulator"})
    session = SimpleNamespace(config=SimpleNamespace(option=SimpleNamespace(collectonly=False)))
    report.pytest_sessionstart(session)
    report.set_target("Requested", "26.4")
    report.set_capabilities(
        {"deviceName": "Resolved", "platformVersion": "27.0", "udid": "private"}
    )
    for nodeid, phase, outcome in [
        ("test_a", "setup", "passed"),
        ("test_a", "call", "passed"),
        ("test_a", "teardown", "failed"),
        ("test_b", "setup", "failed"),
        ("test_b", "teardown", "passed"),
        ("test_c", "setup", "skipped"),
        ("test_d", "call", "passed"),
    ]:
        report.pytest_runtest_logreport(
            SimpleNamespace(
                nodeid=nodeid, when=phase, outcome=outcome, duration=0.125, user_properties=[]
            )
        )
    report.pytest_sessionfinish(session, 1)
    manifest = json.loads((report.root / "run.json").read_text())
    assert manifest["summary"] == {"failed": 2, "skipped": 1, "passed": 1}
    assert manifest["target"] == {
        "kind": "simulator",
        "device_name": "Resolved",
        "platform_version": "27.0",
    }
    assert manifest["results"][2]["phase"] == "teardown"
    assert manifest["results"][2]["duration_seconds"] == 0.125
    assert manifest["exit_status"] == 1
    assert manifest["duration_seconds"] >= 0
    assert "private" not in json.dumps(manifest)


def test_collect_only_has_no_report_or_probes(tmp_path: Path, monkeypatch) -> None:
    """Inspection of selection remains free of device/tool setup."""
    probe = Mock()
    monkeypatch.setattr(run_reporting, "collect_environment", probe)
    report = RunReport(tmp_path / "run-id", tmp_path, True, {})
    session = SimpleNamespace(config=SimpleNamespace(option=SimpleNamespace(collectonly=True)))
    report.pytest_sessionstart(session)
    report.pytest_sessionfinish(session, 0)
    probe.assert_not_called()
    assert not report.root.exists()


def test_report_write_failure_does_not_fail_test(tmp_path: Path, caplog) -> None:
    """Reporting cannot hide the original test outcome if storage is unavailable."""
    root = tmp_path / "not-a-directory"
    root.write_text("occupied")
    report = RunReport(root, tmp_path, False, {})
    report.enabled = True
    report.write()
    assert "Unable to save run manifest" in caplog.text
