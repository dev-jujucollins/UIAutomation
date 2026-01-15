"""
App Launcher utility for managing iOS system apps.
"""

from enum import Enum
from typing import Optional

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

    def launch_by_bundle_id(self, bundle_id: str) -> None:
        """
        Launch an app by bundle identifier.

        Args:
            bundle_id: The app's bundle ID.
        """
        self.driver.activate_app(bundle_id)

    def terminate(self, app: SystemApps) -> bool:
        """
        Terminate a running app.

        Args:
            app: SystemApps enum value.

        Returns:
            True if app was terminated.
        """
        return self.driver.terminate_app(app.value)

    def terminate_by_bundle_id(self, bundle_id: str) -> bool:
        """
        Terminate an app by bundle identifier.

        Args:
            bundle_id: The app's bundle ID.

        Returns:
            True if app was terminated.
        """
        return self.driver.terminate_app(bundle_id)

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

    def is_running(self, app: SystemApps) -> bool:
        """
        Check if an app is currently running (foreground or background).

        Args:
            app: SystemApps enum value.

        Returns:
            True if app is running.
        """
        state = self.get_state(app)
        return state in [
            AppState.FOREGROUND,
            AppState.BACKGROUND,
            AppState.BACKGROUND_SUSPENDED,
        ]

    def is_foreground(self, app: SystemApps) -> bool:
        """
        Check if an app is in the foreground.

        Args:
            app: SystemApps enum value.

        Returns:
            True if app is in foreground.
        """
        return self.get_state(app) == AppState.FOREGROUND

    def background(self, seconds: int = -1) -> None:
        """
        Put current app in background.

        Args:
            seconds: Seconds to stay in background. -1 for indefinite.
        """
        self.driver.background_app(seconds)

    def reset_app(self, app: SystemApps) -> None:
        """
        Reset an app by terminating and relaunching it.

        Args:
            app: SystemApps enum value.
        """
        self.terminate(app)
        self.launch(app)

    # -------------------------------------------------------------------------
    # Convenience methods for common apps
    # -------------------------------------------------------------------------

    def launch_settings(self) -> None:
        """Launch the Settings app."""
        self.launch(SystemApps.SETTINGS)

    def launch_safari(self) -> None:
        """Launch Safari browser."""
        self.launch(SystemApps.SAFARI)

    def launch_contacts(self) -> None:
        """Launch Contacts app."""
        self.launch(SystemApps.CONTACTS)

    def launch_calendar(self) -> None:
        """Launch Calendar app."""
        self.launch(SystemApps.CALENDAR)

    def launch_photos(self) -> None:
        """Launch Photos app."""
        self.launch(SystemApps.PHOTOS)

    def launch_messages(self) -> None:
        """Launch Messages app."""
        self.launch(SystemApps.MESSAGES)

    def launch_notes(self) -> None:
        """Launch Notes app."""
        self.launch(SystemApps.NOTES)

    def launch_reminders(self) -> None:
        """Launch Reminders app."""
        self.launch(SystemApps.REMINDERS)

    def launch_maps(self) -> None:
        """Launch Maps app."""
        self.launch(SystemApps.MAPS)

    def launch_mail(self) -> None:
        """Launch Mail app."""
        self.launch(SystemApps.MAIL)

    def launch_clock(self) -> None:
        """Launch Clock app."""
        self.launch(SystemApps.CLOCK)

    def launch_calculator(self) -> None:
        """Launch Calculator app."""
        self.launch(SystemApps.CALCULATOR)

    def launch_files(self) -> None:
        """Launch Files app."""
        self.launch(SystemApps.FILES)
