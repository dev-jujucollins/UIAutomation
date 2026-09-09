"""Tests for appium service."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uiautomation.utils.appium_service import (
    ensure_xcuitest_driver_installed,
    get_appium_executable,
    is_appium_server_running,
    is_local_appium_url,
    start_appium_service,
    wait_for_appium_server,
)


def test_is_local_appium_url_accepts_localhost() -> None:
    """Localhost Appium URLs should be considered local."""
    assert is_local_appium_url("http://localhost:4723")
    assert is_local_appium_url("http://127.0.0.1:4723/wd/hub")


def test_is_appium_server_running_returns_false_on_network_error() -> None:
    """Appium health check should fail closed on connection errors."""
    with patch("uiautomation.utils.appium_service.urlopen", side_effect=OSError):
        assert is_appium_server_running("http://localhost:4723") is False


def test_wait_for_appium_server_retries_until_ready() -> None:
    """Appium wait should poll until service responds."""
    with patch(
        "uiautomation.utils.appium_service.is_appium_server_running",
        side_effect=[False, False, True],
    ):
        assert wait_for_appium_server(
            "http://localhost:4723",
            timeout_seconds=1.0,
            poll_interval_seconds=0.01,
        )


def test_get_appium_executable_raises_actionable_error_when_missing() -> None:
    """Missing Appium executable should fail with install guidance."""
    with patch("uiautomation.utils.appium_service.which", return_value=None):
        try:
            get_appium_executable()
        except RuntimeError as error:
            assert "npm install -g appium" in str(error)
            assert "appium driver install xcuitest" in str(error)
        else:
            raise AssertionError("Expected RuntimeError")


def test_ensure_xcuitest_driver_installed_accepts_installed_driver() -> None:
    """Installed XCUITest driver should satisfy Appium preflight."""
    result = MagicMock()
    result.stdout = '{"xcuitest": {"installed": true}}'

    with (
        patch("uiautomation.utils.appium_service.which", return_value="/opt/bin/appium"),
        patch(
            "uiautomation.utils.appium_service.subprocess.run", return_value=result
        ) as subprocess_run,
    ):
        ensure_xcuitest_driver_installed()

    subprocess_run.assert_called_once_with(
        ["/opt/bin/appium", "driver", "list", "--installed", "--json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_ensure_xcuitest_driver_installed_raises_actionable_error() -> None:
    """Missing XCUITest driver should fail before session startup."""
    result = MagicMock()
    result.stdout = "{}"

    with (
        patch("uiautomation.utils.appium_service.which", return_value="/opt/bin/appium"),
        patch("uiautomation.utils.appium_service.subprocess.run", return_value=result),
    ):
        try:
            ensure_xcuitest_driver_installed()
        except RuntimeError as error:
            assert "appium driver install xcuitest" in str(error)
        else:
            raise AssertionError("Expected RuntimeError")


def test_managed_start_checks_driver_once_and_closes_parent_log(tmp_path: Path) -> None:
    with (
        patch(
            "uiautomation.utils.appium_service.get_appium_executable", return_value="/bin/appium"
        ),
        patch("uiautomation.utils.appium_service.ensure_xcuitest_driver_installed") as preflight,
        patch("uiautomation.utils.appium_service.subprocess.Popen") as spawn,
        patch("uiautomation.utils.appium_service.wait_for_appium_server", return_value=True),
    ):
        start_appium_service("http://localhost:4723/wd/hub", tmp_path / "appium.log")
    preflight.assert_called_once()
    assert spawn.call_args.kwargs["stdout"].closed
    assert "/wd/hub" in spawn.call_args.args[0]


def test_managed_start_stops_process_when_readiness_check_raises(tmp_path: Path) -> None:
    with (
        patch(
            "uiautomation.utils.appium_service.get_appium_executable", return_value="/bin/appium"
        ),
        patch("uiautomation.utils.appium_service.ensure_xcuitest_driver_installed"),
        patch("uiautomation.utils.appium_service.subprocess.Popen"),
        patch(
            "uiautomation.utils.appium_service.wait_for_appium_server",
            side_effect=RuntimeError("probe"),
        ),
        patch("uiautomation.utils.appium_service.ManagedAppiumService.stop") as stop,
    ):
        with pytest.raises(RuntimeError, match="probe"):
            start_appium_service("http://localhost:4723", tmp_path / "appium.log")
    stop.assert_called_once()
