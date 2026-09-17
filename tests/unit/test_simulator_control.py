"""Tests for simulator control."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from uiautomation.utils import simulator_control as simulators
from uiautomation.utils.simulator_control import (
    SimulatorDevice,
    find_simulator,
    get_preferred_simulator,
    reset_simulator_app_state,
)


@pytest.mark.parametrize("selection", ["environment", "bundle", "xcode-select"])
def test_device_hub_uses_selected_xcode(tmp_path: Path, monkeypatch, selection: str) -> None:
    developer = tmp_path / "Selected Xcode.app" / "Contents" / "Developer"
    hub = developer.parent / "Applications" / "DeviceHub.app"
    hub.mkdir(parents=True)
    monkeypatch.delenv("DEVELOPER_DIR", raising=False)
    if selection != "xcode-select":
        monkeypatch.setenv(
            "DEVELOPER_DIR", str(developer.parent.parent if selection == "bundle" else developer)
        )
    with patch.object(simulators.subprocess, "run") as run:
        run.return_value.stdout = f"{developer}\n"
        simulators.open_simulator_app("device&other=value")
    assert run.call_count == (2 if selection == "xcode-select" else 1)
    if selection == "xcode-select":
        assert run.call_args_list[0].args[0] == ["xcode-select", "-p"]
    run.assert_called_with(
        ["open", "-a", str(hub), "devices:///manage/select?id=device%26other%3Dvalue"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert all(call.kwargs["timeout"] == 30 for call in run.call_args_list)


def test_missing_device_hub_reports_selected_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVELOPER_DIR", str(tmp_path / "Contents" / "Developer"))
    with patch.object(simulators.subprocess, "run") as run:
        with pytest.raises(RuntimeError, match="Device Hub not found.*Select Xcode 27"):
            simulators.open_simulator_app("device")
    run.assert_not_called()


def test_device_hub_launch_failure_propagates(tmp_path: Path, monkeypatch) -> None:
    developer = tmp_path / "Contents" / "Developer"
    (developer.parent / "Applications" / "DeviceHub.app").mkdir(parents=True)
    monkeypatch.setenv("DEVELOPER_DIR", str(developer))
    with patch.object(
        simulators.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "open")
    ):
        with pytest.raises(subprocess.CalledProcessError):
            simulators.open_simulator_app("device")


def test_find_simulator_matches_exact_device_and_version() -> None:
    """Simulator lookup should require exact name and iOS version."""
    simulators = [
        SimulatorDevice("iPhone 16 Pro", "one", "18.5", "Shutdown", True),
        SimulatorDevice("iPhone 17 Pro", "two", "26.2", "Shutdown", True),
    ]
    with patch(
        "uiautomation.utils.simulator_control.list_available_simulators", return_value=simulators
    ):
        simulator = find_simulator("iPhone 16 Pro", "18.5")

    assert simulator == simulators[0]


def test_reset_simulator_app_state_terminates_and_resets_privacy() -> None:
    """Simulator reset should remove manual app and permission state."""
    with patch("uiautomation.utils.simulator_control.subprocess.run") as subprocess_run:
        reset_simulator_app_state("sim-udid", bundle_ids=("com.example.App",))

    subprocess_run.assert_any_call(
        ["xcrun", "simctl", "terminate", "sim-udid", "com.example.App"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    subprocess_run.assert_any_call(
        ["xcrun", "simctl", "privacy", "sim-udid", "reset", "all", "com.example.App"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_get_preferred_simulator_uses_ranked_choice() -> None:
    """Preferred simulator should follow explicit project ranking."""
    simulators = [
        SimulatorDevice("iPhone 17 Pro", "three", "26.4", "Shutdown", True),
        SimulatorDevice("iPhone 17 Pro", "two", "26.2", "Shutdown", True),
        SimulatorDevice("iPhone 16 Pro", "one", "18.5", "Shutdown", True),
    ]
    with patch(
        "uiautomation.utils.simulator_control.list_available_simulators", return_value=simulators
    ):
        simulator = get_preferred_simulator()

    assert simulator == simulators[0]


def test_privacy_reset_failure_is_not_silenced() -> None:
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "privacy" in command:
            assert kwargs["check"] is True
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 1)

    with patch("uiautomation.utils.simulator_control.subprocess.run", side_effect=run):
        with pytest.raises(subprocess.CalledProcessError):
            reset_simulator_app_state("sim-id")


DEVICES = [
    simulators.SimulatorDevice("iPhone 16 Pro", "a", "18.5", "Shutdown", True),
    simulators.SimulatorDevice("Custom Phone", "b", "26.2", "Booted", True),
    simulators.SimulatorDevice("Custom Phone", "c", "26.4", "Shutdown", False),
]


@pytest.mark.parametrize(
    "name, version, expected",
    [
        (None, None, "a"),
        ("Custom Phone", None, "b"),
        (None, "26.2", "b"),
        ("Custom Phone", "26.2", "b"),
    ],
)
def test_target_constraints_are_resolved_together(name, version, expected) -> None:
    with patch.object(simulators, "list_available_simulators", return_value=DEVICES):
        assert simulators.get_preferred_simulator(name, version).udid == expected


@pytest.mark.parametrize(
    "name, version", [("missing", None), ("Custom Phone", "18.5"), (None, "26.4")]
)
def test_mismatches_list_available_targets(name, version) -> None:
    with patch.object(simulators, "list_available_simulators", return_value=DEVICES):
        with pytest.raises(RuntimeError, match="Available:.*Custom Phone.*26.2"):
            simulators.get_preferred_simulator(name, version)


def test_empty_inventory_is_actionable() -> None:
    with patch.object(simulators, "list_available_simulators", return_value=[]):
        with pytest.raises(RuntimeError, match="Available: none"):
            simulators.get_preferred_simulator()


@pytest.mark.parametrize(
    "operation, args, timeouts",
    [
        (simulators.boot_simulator, ("id",), [30, 120]),
        (simulators.shutdown_simulator, ("id",), [30]),
        (simulators.reset_simulator_app_state, ("id", ("app",)), [30, 30]),
    ],
)
def test_simulator_commands_have_bounded_timeouts(operation, args, timeouts) -> None:
    with patch.object(simulators.subprocess, "run") as run:
        operation(*args)
    assert [call.kwargs["timeout"] for call in run.call_args_list] == timeouts


def test_inventory_timeout_propagates_instead_of_selecting_fallback() -> None:
    with patch.object(
        simulators.subprocess, "run", side_effect=subprocess.TimeoutExpired("simctl", 30)
    ) as run:
        with pytest.raises(subprocess.TimeoutExpired):
            simulators.get_preferred_simulator()
    assert run.call_args.kwargs["timeout"] == 30
