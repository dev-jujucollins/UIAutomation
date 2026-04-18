"""Tests for simulator and Appium environment helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.drivers.ios_driver import IOSDriver, IOSDriverConfig
from src.utils.app_launcher import AppState
from src.utils.appium_service import (
    is_appium_server_running,
    is_local_appium_url,
    wait_for_appium_server,
)
from src.utils.simulator_control import SimulatorDevice, find_simulator, get_preferred_simulator


def test_is_local_appium_url_accepts_localhost() -> None:
    """Localhost Appium URLs should be considered local."""
    assert is_local_appium_url("http://localhost:4723")
    assert is_local_appium_url("http://127.0.0.1:4723/wd/hub")


def test_is_appium_server_running_returns_false_on_network_error() -> None:
    """Appium health check should fail closed on connection errors."""
    with patch("src.utils.appium_service.urlopen", side_effect=OSError):
        assert is_appium_server_running("http://localhost:4723") is False


def test_wait_for_appium_server_retries_until_ready() -> None:
    """Appium wait should poll until service responds."""
    with patch(
        "src.utils.appium_service.is_appium_server_running",
        side_effect=[False, False, True],
    ):
        assert wait_for_appium_server(
            "http://localhost:4723",
            timeout_seconds=1.0,
            poll_interval_seconds=0.01,
        )


def test_find_simulator_matches_exact_device_and_version() -> None:
    """Simulator lookup should require exact name and iOS version."""
    simulators = [
        SimulatorDevice("iPhone 16 Pro", "one", "18.5", "Shutdown", True),
        SimulatorDevice("iPhone 17 Pro", "two", "26.2", "Shutdown", True),
    ]
    with patch("src.utils.simulator_control.list_available_simulators", return_value=simulators):
        simulator = find_simulator("iPhone 16 Pro", "18.5")

    assert simulator == simulators[0]


def test_get_preferred_simulator_uses_ranked_choice() -> None:
    """Preferred simulator should follow explicit project ranking."""
    simulators = [
        SimulatorDevice("iPhone 17 Pro", "three", "26.4", "Shutdown", True),
        SimulatorDevice("iPhone 17 Pro", "two", "26.2", "Shutdown", True),
        SimulatorDevice("iPhone 16 Pro", "one", "18.5", "Shutdown", True),
    ]
    with patch("src.utils.simulator_control.list_available_simulators", return_value=simulators):
        simulator = get_preferred_simulator()

    assert simulator == simulators[0]


def test_ios_driver_prepares_simulator_and_local_appium() -> None:
    """Driver should boot simulator and start local Appium when missing."""
    config = IOSDriverConfig(
        device_name="iPhone 17 Pro",
        platform_version="26.4",
        appium_log_path=str(Path("artifacts") / "test-appium.log"),
    )
    driver = IOSDriver(config=config)
    service = MagicMock()
    webdriver_instance = MagicMock()
    simulator = SimulatorDevice("iPhone 17 Pro", "sim-udid", "26.4", "Shutdown", True)

    with (
        patch("src.drivers.ios_driver.find_simulator", return_value=simulator),
        patch("src.drivers.ios_driver.boot_simulator") as boot_simulator,
        patch("src.drivers.ios_driver.open_simulator_app") as open_simulator_app,
        patch("src.drivers.ios_driver.is_appium_server_running", return_value=False),
        patch("src.drivers.ios_driver.start_appium_service", return_value=service),
        patch("src.drivers.ios_driver.webdriver.webdriver.WebDriver", return_value=webdriver_instance),
    ):
        driver.start()

    assert config.udid == "sim-udid"
    boot_simulator.assert_called_once_with("sim-udid")
    open_simulator_app.assert_called_once_with("sim-udid")
    service.stop.assert_not_called()
    driver.quit()
    service.stop.assert_called_once_with()


def test_app_launcher_falls_back_to_simctl_for_simulator_system_apps() -> None:
    """App launcher should use simctl when Appium activation leaves app backgrounded."""
    from src.drivers.ios_driver import SystemApps
    from src.utils.app_launcher import AppLauncher

    driver = MagicMock()
    driver.capabilities = {"udid": "74F15DF3-0787-4D58-BA3B-0FEEFF1DF806"}
    driver.query_app_state.side_effect = [
        AppState.NOT_RUNNING.value,
        AppState.NOT_RUNNING.value,
        AppState.FOREGROUND.value,
    ]
    driver.execute_script.side_effect = RuntimeError("launchApp failed")

    launcher = AppLauncher(driver)

    with patch("src.utils.app_launcher.subprocess.run") as subprocess_run:
        launcher.launch(SystemApps.SETTINGS)

    driver.activate_app.assert_called_once_with(SystemApps.SETTINGS.value)
    subprocess_run.assert_called_once()
