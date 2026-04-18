"""
App Launcher utility for managing iOS system apps.
"""

import subprocess
import time
from enum import Enum

from appium.webdriver.webdriver import WebDriver

from ..drivers.ios_driver import SystemApps


class AppState(Enum):
    """App state codes from Appium."""

    NOT_INSTALLED = 0
    NOT_RUNNING = 1
    BACKGROUND_SUSPENDED = 2
    BACKGROUND = 3
    FOREGROUND = 4


class AppLauncher:
    """
    Utility class for launching and managing iOS apps.

    Provides convenient methods for launching system apps,
    checking app states, and managing app lifecycle.
    """

    def __init__(self, driver: WebDriver):
        """
        Initialize app launcher.

        Args:
            driver: Appium WebDriver instance.
        """
        self.driver = driver

    def launch(self, app: SystemApps) -> None:
        """
        Launch a system app.

        Args:
            app: SystemApps enum value.
        """
        self.driver.activate_app(app.value)
        if self._is_foreground(app):
            return

        try:
            self.driver.execute_script("mobile: launchApp", {"bundleId": app.value})
        except Exception:
            pass
        if self._is_foreground(app):
            return

        if self._launch_with_simctl(app):
            time.sleep(1)
        if not self._is_foreground(app):
            raise RuntimeError(f"Failed to launch {app.value}")

    def terminate(self, app: SystemApps) -> bool:
        """
        Terminate a running app.

        Args:
            app: SystemApps enum value.

        Returns:
            True if app was terminated.
        """
        return self.driver.terminate_app(app.value)

    def get_state(self, app: SystemApps) -> AppState:
        """
        Get the current state of an app.

        Args:
            app: SystemApps enum value.

        Returns:
            AppState enum value.
        """
        state_code = self.driver.query_app_state(app.value)
        return AppState(state_code)

    def _is_foreground(self, app: SystemApps) -> bool:
        """Return whether target app is currently foregrounded."""
        time.sleep(0.5)
        try:
            return self.get_state(app) == AppState.FOREGROUND
        except Exception:
            return False

    def _launch_with_simctl(self, app: SystemApps) -> bool:
        """Fallback to simctl launch for simulator-only system apps."""
        udid = str(self.driver.capabilities.get("udid", ""))
        if "-" not in udid:
            return False

        subprocess.run(  # noqa: S603
            ["xcrun", "simctl", "launch", udid, app.value],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
