"""
iOS Driver configuration for Appium automation of native iOS apps.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from appium import webdriver
from appium.options.ios.xcuitest.base import XCUITestOptions
from appium.webdriver.webdriver import WebDriver

from src.utils.appium_service import (
    ManagedAppiumService,
    is_appium_server_running,
    is_local_appium_url,
    start_appium_service,
)
from src.utils.simulator_control import boot_simulator, find_simulator, open_simulator_app
from src.utils.wda_setup import ensure_prebuilt_wda


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
    platform_version: str = "26.4"
    device_name: str = "iPhone 17 Pro"
    automation_name: str = "XCUITest"
    appium_server_url: str = "http://localhost:4723"
    no_reset: bool = False
    new_command_timeout: int = 300
    wda_launch_timeout: int = 120000
    wda_connection_timeout: int = 240000
    auto_boot_simulator: bool = True
    open_simulator_app: bool = True
    auto_start_appium: bool = True
    prebuild_wda_for_simulator: bool = False
    appium_log_path: str = "artifacts/appium.log"
    derived_data_path: str | None = "artifacts/wda-derived-data"

    # Physical device settings
    udid: str | None = None  # Device UDID (required for physical devices)
    xcode_org_id: str | None = None  # Apple Team ID for signing
    xcode_signing_id: str = "iPhone Developer"  # Signing identity

    # Optional: Use pre-built WebDriverAgent (speeds up test start)
    use_prebuilt_wda: bool = False


class IOSDriver:
    """
    iOS Driver wrapper for Appium automation.

    Provides convenient methods for launching system apps and managing
    the WebDriver session.
    """

    def __init__(
        self,
        config: IOSDriverConfig | None = None,
        bundle_id: str | None = None,
        app: SystemApps | None = None,
    ):
        """
        Initialize iOS driver.

        Args:
            config: Driver configuration. Uses defaults if not provided.
            bundle_id: Bundle ID of app to launch. Takes precedence over `app`.
            app: SystemApps enum value for the app to launch.
        """
        self.config = config or IOSDriverConfig()
        self._driver: WebDriver | None = None
        self._managed_appium_service: ManagedAppiumService | None = None

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

    def _prepare_simulator(self) -> None:
        """Boot configured simulator before starting driver."""
        if self.config.udid or not self.config.auto_boot_simulator:
            return

        simulator = find_simulator(self.config.device_name, self.config.platform_version)
        if simulator is None:
            raise RuntimeError(
                f"Simulator not found for {self.config.device_name} iOS {self.config.platform_version}."
            )

        boot_simulator(simulator.udid)
        if self.config.open_simulator_app:
            open_simulator_app(simulator.udid)
        if self.config.prebuild_wda_for_simulator and self.config.derived_data_path:
            derived_data_path = ensure_prebuilt_wda(Path(self.config.derived_data_path).resolve())
            self.config.use_prebuilt_wda = True
            self.config.derived_data_path = str(derived_data_path)
        self.config.udid = simulator.udid

    def _ensure_appium_server(self) -> None:
        """Start local Appium service when configured and needed."""
        server_url = self.config.appium_server_url
        if is_appium_server_running(server_url):
            return

        if not self.config.auto_start_appium or not is_local_appium_url(server_url):
            raise RuntimeError(f"Appium server not reachable at {server_url}.")

        self._managed_appium_service = start_appium_service(
            server_url=server_url,
            log_path=Path(self.config.appium_log_path),
        )

    def start(self) -> "IOSDriver":
        """
        Start the Appium driver session.

        Returns:
            Self for method chaining.
        """
        self._prepare_simulator()
        self._ensure_appium_server()
        options = self._build_options()
        self._driver = webdriver.webdriver.WebDriver(
            command_executor=self.config.appium_server_url, options=options
        )
        return self

    def quit(self) -> None:
        """Quit the driver session."""
        if self._driver:
            self._driver.quit()
            self._driver = None
        if self._managed_appium_service:
            self._managed_appium_service.stop()
            self._managed_appium_service = None

    def __enter__(self) -> "IOSDriver":
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.quit()
