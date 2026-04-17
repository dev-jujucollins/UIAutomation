"""
App Launcher utility for managing iOS system apps.
"""

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

    Provides methods for launching system apps, checking app states,
    and managing app lifecycle.
    """

    def __init__(self, driver: WebDriver):
        self.driver = driver

    def launch(self, app: SystemApps) -> None:
        """Launch a system app."""
        self.driver.activate_app(app.value)

    def terminate(self, app: SystemApps) -> bool:
        """Terminate a running app."""
        return self.driver.terminate_app(app.value)

    def get_state(self, app: SystemApps) -> AppState:
        """Get the current state of an app."""
        return AppState(self.driver.query_app_state(app.value))

    def is_running(self, app: SystemApps) -> bool:
        """Check if an app is currently running (foreground or background)."""
        return self.get_state(app) in (
            AppState.FOREGROUND,
            AppState.BACKGROUND,
            AppState.BACKGROUND_SUSPENDED,
        )

    def is_foreground(self, app: SystemApps) -> bool:
        """Check if an app is in the foreground."""
        return self.get_state(app) == AppState.FOREGROUND

    def background(self, seconds: int = -1) -> None:
        """Put current app in background. -1 for indefinite."""
        self.driver.background_app(seconds)

    def reset_app(self, app: SystemApps) -> None:
        """Reset an app by terminating and relaunching it."""
        self.terminate(app)
        self.launch(app)
