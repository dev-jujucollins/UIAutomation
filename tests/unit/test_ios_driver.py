"""Tests for ios driver."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uiautomation.drivers.ios_driver import IOSDriver, IOSDriverConfig
from uiautomation.utils.simulator_control import (
    SimulatorDevice,
)


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
        patch("uiautomation.drivers.ios_driver.find_simulator", return_value=simulator),
        patch("uiautomation.drivers.ios_driver.boot_simulator") as boot_simulator,
        patch("uiautomation.drivers.ios_driver.shutdown_simulator") as shutdown_simulator,
        patch("uiautomation.drivers.ios_driver.reset_simulator_app_state") as reset_simulator_state,
        patch("uiautomation.drivers.ios_driver.open_simulator_app") as open_simulator_app,
        patch("uiautomation.drivers.ios_driver.is_appium_server_running", return_value=False),
        patch("uiautomation.drivers.ios_driver.start_appium_service", return_value=service),
        patch(
            "uiautomation.drivers.ios_driver.webdriver.webdriver.WebDriver",
            return_value=webdriver_instance,
        ),
    ):
        driver.start()

    assert config.udid == "sim-udid"
    boot_simulator.assert_called_once_with("sim-udid")
    shutdown_simulator.assert_not_called()
    reset_simulator_state.assert_called_once_with("sim-udid")
    open_simulator_app.assert_called_once_with("sim-udid")
    service.stop.assert_not_called()
    driver.quit()
    service.stop.assert_called_once_with()


def test_ios_driver_can_skip_simulator_state_reset() -> None:
    """Driver should preserve simulator state when reset is disabled."""
    config = IOSDriverConfig(
        device_name="iPhone 17 Pro",
        platform_version="26.4",
        reset_simulator_state=False,
    )
    driver = IOSDriver(config=config)
    simulator = SimulatorDevice("iPhone 17 Pro", "sim-udid", "26.4", "Shutdown", True)

    with (
        patch("uiautomation.drivers.ios_driver.find_simulator", return_value=simulator),
        patch("uiautomation.drivers.ios_driver.boot_simulator"),
        patch("uiautomation.drivers.ios_driver.reset_simulator_app_state") as reset_simulator_state,
        patch("uiautomation.drivers.ios_driver.open_simulator_app"),
        patch("uiautomation.drivers.ios_driver.is_appium_server_running", return_value=True),
        patch(
            "uiautomation.drivers.ios_driver.webdriver.webdriver.WebDriver",
            return_value=MagicMock(),
        ),
    ):
        driver.start()

    reset_simulator_state.assert_not_called()


def test_ios_driver_restarts_booted_simulator_when_requested() -> None:
    """Fresh simulator sessions should not inherit a stuck booted runtime."""
    config = IOSDriverConfig(
        device_name="iPhone 17 Pro", platform_version="26.4", restart_simulator=True
    )
    driver = IOSDriver(config=config)
    simulator = SimulatorDevice("iPhone 17 Pro", "sim-udid", "26.4", "Booted", True)

    with (
        patch("uiautomation.drivers.ios_driver.find_simulator", return_value=simulator),
        patch("uiautomation.drivers.ios_driver.shutdown_simulator") as shutdown_simulator,
        patch("uiautomation.drivers.ios_driver.boot_simulator") as boot_simulator,
        patch("uiautomation.drivers.ios_driver.reset_simulator_app_state"),
        patch("uiautomation.drivers.ios_driver.open_simulator_app"),
        patch("uiautomation.drivers.ios_driver.is_appium_server_running", return_value=True),
        patch(
            "uiautomation.drivers.ios_driver.webdriver.webdriver.WebDriver",
            return_value=MagicMock(),
        ),
    ):
        driver.start()

    shutdown_simulator.assert_called_once_with("sim-udid")
    boot_simulator.assert_called_once_with("sim-udid")


def test_ios_driver_wraps_session_start_errors_with_appium_log(tmp_path: Path) -> None:
    """Session start failures should include recent Appium diagnostics."""
    log_path = tmp_path / "appium.log"
    log_path.write_text("old\nWebDriverAgent failed\n", encoding="utf-8")
    config = IOSDriverConfig(
        device_name="iPhone 17 Pro",
        platform_version="26.4",
        appium_log_path=str(log_path),
        reset_simulator_state=False,
    )
    driver = IOSDriver(config=config)
    simulator = SimulatorDevice("iPhone 17 Pro", "sim-udid", "26.4", "Shutdown", True)

    with (
        patch("uiautomation.drivers.ios_driver.find_simulator", return_value=simulator),
        patch("uiautomation.drivers.ios_driver.boot_simulator"),
        patch("uiautomation.drivers.ios_driver.open_simulator_app"),
        patch("uiautomation.drivers.ios_driver.is_appium_server_running", return_value=True),
        patch(
            "uiautomation.drivers.ios_driver.webdriver.webdriver.WebDriver",
            side_effect=ConnectionError("closed"),
        ),
    ):
        try:
            driver.start()
        except RuntimeError as error:
            assert "Failed to start iOS Appium session" in str(error)
            assert "WebDriverAgent failed" in str(error)
        else:
            raise AssertionError("Expected RuntimeError")


def test_existing_server_needs_no_local_appium_installation() -> None:
    wrapper = IOSDriver()
    with (
        patch("uiautomation.drivers.ios_driver.is_appium_server_running", return_value=True),
        patch(
            "uiautomation.utils.appium_service.which",
            side_effect=AssertionError("unneeded CLI lookup"),
        ),
    ):
        wrapper._ensure_appium_server()


def test_startup_preserves_original_error_when_logs_and_cleanup_fail(tmp_path: Path) -> None:
    wrapper = IOSDriver(IOSDriverConfig(appium_log_path=str(tmp_path)))
    original = ConnectionError("device disconnected")
    wrapper._prepare_simulator = MagicMock()
    wrapper._ensure_appium_server = MagicMock()
    wrapper.quit = MagicMock(side_effect=RuntimeError("cleanup failed"))
    with patch(
        "uiautomation.drivers.ios_driver.webdriver.webdriver.WebDriver", side_effect=original
    ):
        with pytest.raises(RuntimeError, match="Failed to start") as caught:
            wrapper.start()
    assert caught.value.__cause__ is original
    wrapper.quit.assert_called_once()


def test_build_options_failure_still_cleans_up() -> None:
    wrapper = IOSDriver()
    wrapper._prepare_simulator = MagicMock()
    wrapper._ensure_appium_server = MagicMock()
    wrapper._build_options = MagicMock(side_effect=ValueError("bad options"))
    wrapper.quit = MagicMock()
    with pytest.raises(RuntimeError, match="Failed to start"):
        wrapper.start()
    wrapper.quit.assert_called_once()


def test_driver_config_defaults_to_resetting_state() -> None:
    """Driver sessions should reset state unless explicitly overridden."""
    config = IOSDriverConfig()
    assert config.no_reset is False


def test_quit_stops_owned_server_when_session_quit_fails() -> None:
    """Broken device connections must not leak an owned Appium process."""
    wrapper = IOSDriver()
    driver, service = MagicMock(), MagicMock()
    wrapper._driver = driver
    wrapper._managed_appium_service = service
    driver.quit.side_effect = RuntimeError("connection lost")
    with pytest.raises(RuntimeError, match="connection lost"):
        wrapper.quit()
    service.stop.assert_called_once()
    wrapper.quit()
    service.stop.assert_called_once()


def test_booted_simulator_is_reused_with_app_state_reset() -> None:
    """Normal startup should reset app state without restarting the runtime."""
    wrapper = IOSDriver(IOSDriverConfig(open_simulator_app=False))
    simulator = SimulatorDevice("iPhone", "sim-id", "26.4", "Booted", True)
    with (
        patch("uiautomation.drivers.ios_driver.find_simulator", return_value=simulator),
        patch("uiautomation.drivers.ios_driver.shutdown_simulator") as shutdown,
        patch("uiautomation.drivers.ios_driver.boot_simulator") as boot,
        patch("uiautomation.drivers.ios_driver.reset_simulator_app_state") as reset,
    ):
        wrapper._prepare_simulator()
    shutdown.assert_not_called()
    boot.assert_called_once_with("sim-id")
    reset.assert_called_once_with("sim-id")
