"""Tests for app launcher."""

from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import WebDriverException

from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.utils.app_launcher import AppLauncher, AppState
from uiautomation.utils.simulator_control import SimulatorDevice


def test_app_launcher_falls_back_to_simctl_for_simulator_system_apps() -> None:
    """App launcher should use simctl when Appium activation leaves app backgrounded."""
    driver = MagicMock()
    driver.capabilities = {"udid": "74F15DF3-0787-4D58-BA3B-0FEEFF1DF806"}
    driver.query_app_state.side_effect = [
        AppState.NOT_RUNNING.value,
        AppState.NOT_RUNNING.value,
        AppState.FOREGROUND.value,
    ]
    driver.execute_script.side_effect = WebDriverException("launchApp failed")

    launcher = AppLauncher(driver)
    launcher.LAUNCH_TIMEOUT = 0
    simulator = SimulatorDevice("iPhone", driver.capabilities["udid"], "27.0", "Booted", True)

    with (
        patch("uiautomation.utils.app_launcher.subprocess.run") as subprocess_run,
        patch(
            "uiautomation.utils.app_launcher.list_available_simulators", return_value=[simulator]
        ),
    ):
        launcher.launch(SystemApps.SETTINGS)

    driver.activate_app.assert_called_once_with(SystemApps.SETTINGS.value)
    subprocess_run.assert_called_once()


@pytest.mark.parametrize("udid", ["00008150-0002794C3A08401C", "unknown-simulator-id", ""])
def test_simctl_fallback_requires_a_known_local_simulator(udid: str) -> None:
    driver = MagicMock(capabilities={"udid": udid})
    simulator = SimulatorDevice("iPhone", "known-simulator", "27.0", "Booted", True)
    with (
        patch(
            "uiautomation.utils.app_launcher.list_available_simulators", return_value=[simulator]
        ),
        patch("uiautomation.utils.app_launcher.subprocess.run") as run,
    ):
        assert AppLauncher(driver)._launch_with_simctl(SystemApps.SETTINGS) is False
    run.assert_not_called()


def test_simctl_fallback_without_local_xcode_returns_false() -> None:
    driver = MagicMock(capabilities={"udid": "remote-target"})
    with patch(
        "uiautomation.utils.app_launcher.list_available_simulators", side_effect=FileNotFoundError
    ):
        assert AppLauncher(driver)._launch_with_simctl(SystemApps.SETTINGS) is False


def test_launch_waits_for_foreground_without_running_fallbacks() -> None:
    driver = MagicMock()
    driver.query_app_state.side_effect = [AppState.BACKGROUND.value, AppState.FOREGROUND.value]
    with patch("uiautomation.utils.app_launcher.list_available_simulators") as inventory:
        AppLauncher(driver).launch(SystemApps.CALENDAR)
    driver.execute_script.assert_not_called()
    inventory.assert_not_called()


def test_app_state_connection_errors_are_not_reported_as_background() -> None:
    driver = MagicMock()
    driver.query_app_state.side_effect = WebDriverException("device disconnected")
    with pytest.raises(WebDriverException, match="device disconnected"):
        AppLauncher(driver).launch(SystemApps.CALENDAR)
