"""Tests for environment diagnostics without local tools or devices."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from uiautomation import cli
from uiautomation.utils import doctor


@pytest.fixture
def environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Provide a working host with deterministic external command responses."""
    developer = tmp_path / "Xcode.app" / "Contents" / "Developer"
    hub = developer.parent / "Applications" / "DeviceHub.app"
    hub.mkdir(parents=True)
    monkeypatch.setenv("DEVELOPER_DIR", str(developer))
    monkeypatch.setattr(doctor.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(doctor, "get_appium_executable", lambda: "/bin/appium")
    outputs = {
        ("node", "--version"): "v26.10.0",
        ("xcode-select", "-p"): str(developer),
        ("xcodebuild", "-version"): "Xcode 27.1\nBuild version 27A9269",
        ("/bin/appium", "--version"): "3.8.0",
        ("/bin/appium", "driver", "list", "--installed", "--json"): json.dumps(
            {"xcuitest": {"installed": True, "version": "10.43.1"}}
        ),
        ("/bin/appium", "driver", "doctor", "xcuitest"): "All required checks passed",
        ("xcrun", "simctl", "list", "devices", "available", "-j"): json.dumps(
            {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-27-0": [
                        {"name": "iPhone 18 Pro", "udid": "sim-a", "state": "Shutdown"},
                        {"name": "iPhone 17 Pro", "udid": "sim-b", "state": "Booted"},
                    ]
                }
            }
        ),
    }

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["check"] is True
        assert kwargs["timeout"] in {30, 60}
        value = outputs[tuple(command)]
        if isinstance(value, Exception):
            raise value
        return subprocess.CompletedProcess(command, 0, stdout=value, stderr="")

    runner = MagicMock(side_effect=run)
    monkeypatch.setattr(doctor.subprocess, "run", runner)
    response = MagicMock()
    response.status = 200
    response.read.return_value = '{"value": {"ready": true}}'
    response.__enter__.return_value = response
    opener = MagicMock(return_value=response)
    monkeypatch.setattr(doctor, "urlopen", opener)
    return {
        "outputs": outputs,
        "runner": runner,
        "response": response,
        "opener": opener,
        "hub": hub,
    }


def test_default_checks_select_target_without_mutating_host(environment: dict) -> None:
    report = doctor.diagnose_environment()

    assert report.ok
    assert report.selected_simulator is not None
    assert report.selected_simulator.name == "iPhone 18 Pro"
    assert len(report.simulators) == 2
    commands = [call.args[0] for call in environment["runner"].call_args_list]
    assert ["/bin/appium", "driver", "doctor", "xcuitest"] not in commands
    assert not any(
        set(command) & {"boot", "open", "create", "install", "shutdown"} for command in commands
    )
    assert "No iOS test session was started" in doctor.format_report(report)


def test_target_filters_match_pytest_selection(environment: dict) -> None:
    report = doctor.diagnose_environment(device_name="iPhone 17 Pro", platform_version="27.0")
    assert report.ok
    assert report.selected_simulator is not None
    assert report.selected_simulator.udid == "sim-b"


def test_missing_target_fails_with_inventory_and_remedy(environment: dict) -> None:
    report = doctor.diagnose_environment(device_name="Missing iPhone")
    assert not report.ok
    assert report.selected_simulator is None
    assert len(report.simulators) == 2
    result = next(check for check in report.checks if check.name == "Simulator")
    assert "Missing iPhone" in result.detail
    assert result.remedy is not None and "Device Hub" in result.remedy


@pytest.mark.parametrize("headless,ok", [(False, False), (True, True)])
def test_missing_device_hub_only_blocks_visible_runs(
    environment: dict, headless: bool, ok: bool
) -> None:
    environment["hub"].rmdir()
    assert doctor.diagnose_environment(headless=headless).ok is ok


@pytest.mark.parametrize("selection", ["xcode-select", "bundle"])
def test_xcode_selection_sources(
    environment: dict, monkeypatch: pytest.MonkeyPatch, selection: str
) -> None:
    if selection == "xcode-select":
        monkeypatch.delenv("DEVELOPER_DIR")
    else:
        monkeypatch.setenv("DEVELOPER_DIR", str(environment["hub"].parents[2]))
    assert doctor.diagnose_environment().ok


def test_old_xcode_fails_required_version(environment: dict) -> None:
    environment["outputs"][("xcodebuild", "-version")] = "Xcode 26.4"
    report = doctor.diagnose_environment()
    assert not report.ok
    assert "Xcode 27+ required" in doctor.format_report(report)


@pytest.mark.parametrize("payload", ["{}", "[]", "invalid", '{"xcuitest": null}'])
def test_bad_or_missing_driver_fails_with_install_guidance(environment: dict, payload: str) -> None:
    environment["outputs"][("/bin/appium", "driver", "list", "--installed", "--json")] = payload
    report = doctor.diagnose_environment(run_driver_doctor=True)
    assert not report.ok
    assert "appium driver install xcuitest" in doctor.format_report(report)
    assert ["/bin/appium", "driver", "doctor", "xcuitest"] not in [
        call.args[0] for call in environment["runner"].call_args_list
    ]


def test_missing_tools_report_errors_without_stopping_other_checks(environment: dict) -> None:
    environment["outputs"][("node", "--version")] = FileNotFoundError("node missing")
    environment["outputs"][("xcodebuild", "-version")] = subprocess.TimeoutExpired("xcodebuild", 30)
    environment["outputs"][("/bin/appium", "--version")] = subprocess.CalledProcessError(
        1, "appium", stderr="Appium home inaccessible"
    )
    report = doctor.diagnose_environment()
    assert not report.ok
    text = doctor.format_report(report)
    assert "node missing" in text
    assert "Timed out after 30s" in text
    assert "Appium home inaccessible" in text
    assert any(check.name == "Appium server" and check.status == "pass" for check in report.checks)


def test_upstream_doctor_only_runs_after_explicit_opt_in(environment: dict) -> None:
    report = doctor.diagnose_environment(run_driver_doctor=True)
    assert report.ok
    calls = [
        call
        for call in environment["runner"].call_args_list
        if call.args[0] == ["/bin/appium", "driver", "doctor", "xcuitest"]
    ]
    assert len(calls) == 1
    assert calls[0].kwargs["timeout"] == 60


def test_upstream_doctor_timeout_is_failure(environment: dict) -> None:
    environment["outputs"][("/bin/appium", "driver", "doctor", "xcuitest")] = (
        subprocess.TimeoutExpired("appium", 60)
    )
    report = doctor.diagnose_environment(run_driver_doctor=True)
    assert not report.ok
    assert "Timed out after 60s" in doctor.format_report(report)


@pytest.mark.parametrize("require_server,expected", [(False, "warn"), (True, "fail")])
def test_unavailable_local_server_can_be_autostarted(
    environment: dict, require_server: bool, expected: str
) -> None:
    environment["opener"].side_effect = OSError("Connection refused")
    report = doctor.diagnose_environment(require_server=require_server)
    result = next(check for check in report.checks if check.name == "Appium server")
    assert result.status == expected
    assert report.ok is (not require_server)


def test_unavailable_remote_server_is_required_failure(environment: dict) -> None:
    environment["opener"].side_effect = OSError("Connection refused")
    assert not doctor.diagnose_environment(server_url="https://appium.example.test").ok


def test_ipv6_localhost_fails_when_framework_cannot_autostart_it(environment: dict) -> None:
    environment["opener"].side_effect = OSError("Connection refused")
    assert not doctor.diagnose_environment(server_url="http://[::1]:4723").ok


@pytest.mark.parametrize(
    "payload", ['{"value": {"ready": false}}', '{"value": {}}', "[]", "not JSON"]
)
def test_http_success_alone_does_not_prove_server_readiness(
    environment: dict, payload: str
) -> None:
    environment["response"].read.return_value = payload
    assert not doctor.diagnose_environment().ok


def test_upstream_doctor_includes_diagnostics_from_stderr(
    environment: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout="", stderr="Optional dependency missing"
        ),
    )
    assert (
        doctor._command(["appium", "driver", "doctor", "xcuitest"], include_stderr=True)
        == "Optional dependency missing"
    )


def test_custom_server_base_path_is_preserved(environment: dict) -> None:
    assert doctor.diagnose_environment(server_url="http://localhost:4723/wd/hub/").ok
    environment["opener"].assert_called_once_with("http://localhost:4723/wd/hub/status", timeout=3)


@pytest.mark.parametrize(
    "url",
    ["localhost:4723", "file:///tmp/secret", "http://localhost:bad", "http://localhost/?query=1"],
)
def test_invalid_url_is_actionable_failure_without_request(environment: dict, url: str) -> None:
    assert not doctor.diagnose_environment(server_url=url).ok
    environment["opener"].assert_not_called()


def test_cli_json_contains_inventory_and_returns_failure(
    environment: dict, capsys: pytest.CaptureFixture
) -> None:
    exit_code = cli.main(["doctor", "--device-name", "missing", "--json"])
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["ok"] is False
    assert result["selected_simulator"] is None
    assert len(result["simulators"]) == 2


def test_cli_passes_target_context_and_returns_success(
    environment: dict, capsys: pytest.CaptureFixture
) -> None:
    exit_code = cli.main(
        [
            "doctor",
            "--device-name",
            "iPhone 17 Pro",
            "--platform-version",
            "27.0",
            "--headless-simulator",
            "--require-server",
            "--appium-server",
            "http://localhost:4723/custom",
        ]
    )
    assert exit_code == 0
    assert "iPhone 17 Pro" in capsys.readouterr().out
    environment["opener"].assert_called_once_with("http://localhost:4723/custom/status", timeout=3)
