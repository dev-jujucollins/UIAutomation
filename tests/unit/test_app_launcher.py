"""Tests for app launcher."""

from unittest.mock import MagicMock, patch

from uiautomation.utils.app_launcher import AppState


def test_app_launcher_falls_back_to_simctl_for_simulator_system_apps() -> None:
    """App launcher should use simctl when Appium activation leaves app backgrounded."""
    from uiautomation.drivers.ios_driver import SystemApps
    from uiautomation.utils.app_launcher import AppLauncher

    driver = MagicMock()
    driver.capabilities = {"udid": "74F15DF3-0787-4D58-BA3B-0FEEFF1DF806"}
    driver.query_app_state.side_effect = [
        AppState.NOT_RUNNING.value,
        AppState.NOT_RUNNING.value,
        AppState.FOREGROUND.value,
    ]
    driver.execute_script.side_effect = RuntimeError("launchApp failed")

    launcher = AppLauncher(driver)

    with patch("uiautomation.utils.app_launcher.subprocess.run") as subprocess_run:
        launcher.launch(SystemApps.SETTINGS)

    driver.activate_app.assert_called_once_with(SystemApps.SETTINGS.value)
    subprocess_run.assert_called_once()
