"""
iOS Driver configuration for Appium automation of native iOS apps.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.webdriver import WebDriver


class SystemApps(Enum):
    """Bundle identifiers for iOS system apps."""

    SETTINGS = "com.apple.Preferences"
    SAFARI = "com.apple.mobilesafari"
    CONTACTS = "com.apple.MobileAddressBook"
    CALENDAR = "com.apple.mobilecal"
    PHOTOS = "com.apple.Photos"
    MESSAGES = "com.apple.MobileSMS"
    PHONE = "com.apple.mobilephone"
    FACETIME = "com.apple.facetime"
    MAIL = "com.apple.mobilemail"
    NOTES = "com.apple.mobilenotes"
    REMINDERS = "com.apple.reminders"
    CLOCK = "com.apple.mobiletimer"
    MAPS = "com.apple.Maps"
    WEATHER = "com.apple.weather"
    CALCULATOR = "com.apple.calculator"
    CAMERA = "com.apple.camera"
    APP_STORE = "com.apple.AppStore"
    HEALTH = "com.apple.Health"
    WALLET = "com.apple.Passbook"
    FILES = "com.apple.DocumentsApp"


@dataclass
class IOSDriverConfig:
    """Configuration for iOS driver."""

    platform_name: str = "iOS"
    platform_version: str = "17.0"
    device_name: str = "iPhone 15"
    automation_name: str = "XCUITest"
    appium_server_url: str = "http://localhost:4723"
    no_reset: bool = True
    new_command_timeout: int = 300
    wda_launch_timeout: int = 120000
    wda_connection_timeout: int = 240000

    # Physical device settings
    udid: Optional[str] = None  # Device UDID (required for physical devices)
    xcode_org_id: Optional[str] = None  # Apple Team ID for signing
    xcode_signing_id: str = "iPhone Developer"  # Signing identity

    # Optional: Use pre-built WebDriverAgent (speeds up test start)
    use_prebuilt_wda: bool = False
    derived_data_path: Optional[str] = None  # Path to WDA derived data


class IOSDriver:
    """
    iOS Driver wrapper for Appium automation.

    Provides convenient methods for launching system apps and managing
    the WebDriver session.
    """

    def __init__(
        self,
        config: Optional[IOSDriverConfig] = None,
        bundle_id: Optional[str] = None,
        app: Optional[SystemApps] = None,
    ):
        """
        Initialize iOS driver.

        Args:
            config: Driver configuration. Uses defaults if not provided.
            bundle_id: Bundle ID of app to launch. Takes precedence over `app`.
            app: SystemApps enum value for the app to launch.
        """
        self.config = config or IOSDriverConfig()
        self._driver: Optional[WebDriver] = None

        # Determine bundle ID
        if bundle_id:
            self._bundle_id = bundle_id
        elif app:
            self._bundle_id = app.value
        else:
            self._bundle_id = None

    @property
    def driver(self) -> WebDriver:
        """Get the underlying Appium WebDriver instance."""
        if self._driver is None:
            raise RuntimeError("Driver not started. Call start() first.")
        return self._driver

    def _build_options(self) -> XCUITestOptions:
        """Build XCUITest options from configuration."""
        options = XCUITestOptions()
        options.platform_name = self.config.platform_name
        options.platform_version = self.config.platform_version
        options.device_name = self.config.device_name
        options.automation_name = self.config.automation_name
        options.no_reset = self.config.no_reset
        options.new_command_timeout = self.config.new_command_timeout

        # WDA timeouts for stability
        options.set_capability("wdaLaunchTimeout", self.config.wda_launch_timeout)
        options.set_capability("wdaConnectionTimeout", self.config.wda_connection_timeout)

        # Physical device configuration
        if self.config.udid:
            options.udid = self.config.udid

            # Code signing for physical devices
            if self.config.xcode_org_id:
                options.set_capability("xcodeOrgId", self.config.xcode_org_id)
                options.set_capability("xcodeSigningId", self.config.xcode_signing_id)

        # Use pre-built WDA for faster startup
        if self.config.use_prebuilt_wda and self.config.derived_data_path:
            options.set_capability("usePrebuiltWDA", True)
            options.set_capability("derivedDataPath", self.config.derived_data_path)

        # Set bundle ID if provided
        if self._bundle_id:
            options.set_capability("bundleId", self._bundle_id)

        return options

    def start(self) -> "IOSDriver":
        """
        Start the Appium driver session.

        Returns:
            Self for method chaining.
        """
        options = self._build_options()
        self._driver = webdriver.Remote(
            command_executor=self.config.appium_server_url, options=options
        )
        return self

    def quit(self) -> None:
        """Quit the driver session."""
        if self._driver:
            self._driver.quit()
            self._driver = None

    def launch_app(self, app: SystemApps) -> None:
        """
        Launch a system app by its enum value.

        Args:
            app: SystemApps enum value.
        """
        self.driver.activate_app(app.value)

    def launch_app_by_bundle_id(self, bundle_id: str) -> None:
        """
        Launch an app by its bundle identifier.

        Args:
            bundle_id: The app's bundle identifier.
        """
        self.driver.activate_app(bundle_id)

    def terminate_app(self, app: SystemApps) -> bool:
        """
        Terminate a running app.

        Args:
            app: SystemApps enum value.

        Returns:
            True if the app was terminated, False otherwise.
        """
        return self.driver.terminate_app(app.value)

    def is_app_installed(self, app: SystemApps) -> bool:
        """
        Check if an app is installed.

        Args:
            app: SystemApps enum value.

        Returns:
            True if installed, False otherwise.
        """
        return self.driver.is_app_installed(app.value)

    def get_app_state(self, app: SystemApps) -> int:
        """
        Get the state of an app.

        Args:
            app: SystemApps enum value.

        Returns:
            App state code:
            - 0: Not installed
            - 1: Not running
            - 2: Running in background (suspended)
            - 3: Running in background
            - 4: Running in foreground
        """
        return self.driver.query_app_state(app.value)

    def background_app(self, seconds: int = -1) -> None:
        """
        Put the app in the background.

        Args:
            seconds: How long to background. -1 means indefinitely.
        """
        self.driver.background_app(seconds)

    def __enter__(self) -> "IOSDriver":
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.quit()
