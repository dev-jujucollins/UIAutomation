"""
Pytest fixtures for iOS UI Automation tests.
"""

import os
from collections.abc import Generator

import pytest

from src.drivers.ios_driver import IOSDriver, IOSDriverConfig, SystemApps
from src.pages.calendar import CalendarHomePage, CalendarOnboardingPage
from src.pages.settings import SettingsHomePage
from src.utils.app_launcher import AppLauncher

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--device-name",
        action="store",
        default="iPhone 15",
        help="iOS device name (default: iPhone 15)",
    )
    parser.addoption(
        "--platform-version",
        action="store",
        default="17.0",
        help="iOS platform version (default: 17.0)",
    )
    parser.addoption(
        "--appium-server",
        action="store",
        default="http://localhost:4723",
        help="Appium server URL (default: http://localhost:4723)",
    )
    # Physical device options
    parser.addoption(
        "--udid",
        action="store",
        default=None,
        help="Device UDID for physical device testing (omit for simulator)",
    )
    parser.addoption(
        "--team-id",
        action="store",
        default=None,
        help="Apple Developer Team ID for code signing (required for physical devices)",
    )


@pytest.fixture(scope="session")
def driver_config(request) -> IOSDriverConfig:
    """
    Create driver configuration from command line options.

    Returns:
        IOSDriverConfig instance.
    """
    udid = request.config.getoption("--udid")
    team_id = request.config.getoption("--team-id")

    config = IOSDriverConfig(
        device_name=request.config.getoption("--device-name"),
        platform_version=request.config.getoption("--platform-version"),
        appium_server_url=request.config.getoption("--appium-server"),
        udid=udid,
        xcode_org_id=team_id,
    )

    # Warn if physical device without team ID
    if udid and not team_id:
        print("\n⚠️  WARNING: Physical device UDID provided without --team-id.")
        print("   WebDriverAgent signing may fail. Get your Team ID from:")
        print("   Xcode > Preferences > Accounts > Your Apple ID > Team ID\n")

    return config


# -------------------------------------------------------------------------
# Driver Fixtures
# -------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ios_driver(driver_config: IOSDriverConfig) -> Generator[IOSDriver, None, None]:
    """
    Create and manage iOS driver session for entire test session.

    Yields:
        IOSDriver instance.
    """
    driver = IOSDriver(config=driver_config)
    driver.start()

    yield driver

    driver.quit()


@pytest.fixture(scope="function")
def driver(ios_driver: IOSDriver):
    """
    Provide the underlying WebDriver for individual tests.

    This fixture provides fresh state by returning to home between tests
    if needed.

    Returns:
        Appium WebDriver instance.
    """
    return ios_driver.driver


@pytest.fixture(scope="function")
def app_launcher(driver) -> AppLauncher:
    """
    Provide app launcher utility.

    Returns:
        AppLauncher instance.
    """
    return AppLauncher(driver)


# -------------------------------------------------------------------------
# App-Specific Fixtures
# -------------------------------------------------------------------------


@pytest.fixture(scope="function")
def settings_app(driver, app_launcher: AppLauncher) -> Generator[SettingsHomePage, None, None]:
    """Launch Settings app and provide home page object."""
    app_launcher.launch(SystemApps.SETTINGS)
    settings_home = SettingsHomePage(driver)
    assert settings_home.is_on_settings_home(), "Failed to launch Settings app"

    yield settings_home

    app_launcher.terminate(SystemApps.SETTINGS)


@pytest.fixture(scope="function")
def calendar_app(driver, app_launcher: AppLauncher) -> Generator:
    """
    Launch Calendar and provide raw driver with onboarding dismissed.

    Use when you need direct driver access (e.g. locator inspection).
    Prefer `calendar_home` for test code.
    """
    app_launcher.launch(SystemApps.CALENDAR)
    CalendarOnboardingPage(driver).dismiss_all_onboarding()

    yield driver

    app_launcher.terminate(SystemApps.CALENDAR)


@pytest.fixture(scope="function")
def calendar_home(driver, app_launcher: AppLauncher) -> Generator[CalendarHomePage, None, None]:
    """Launch Calendar app and provide home page object with onboarding dismissed."""
    app_launcher.launch(SystemApps.CALENDAR)
    CalendarOnboardingPage(driver).dismiss_all_onboarding()

    yield CalendarHomePage(driver)

    app_launcher.terminate(SystemApps.CALENDAR)


# -------------------------------------------------------------------------
# Utility Fixtures
# -------------------------------------------------------------------------


@pytest.fixture(scope="session")
def screenshots_dir() -> str:
    """
    Create and return screenshots directory path.

    Returns:
        Path to screenshots directory.
    """
    screenshots_path = os.path.join(os.path.dirname(__file__), "..", "screenshots")
    os.makedirs(screenshots_path, exist_ok=True)
    return screenshots_path


@pytest.fixture(autouse=True)
def test_logging(request):
    """Log test start and end."""
    print(f"\n{'=' * 60}")
    print(f"Starting test: {request.node.name}")
    print(f"{'=' * 60}")

    yield

    print(f"\n{'=' * 60}")
    print(f"Finished test: {request.node.name}")
    print(f"{'=' * 60}")


# -------------------------------------------------------------------------
# Hooks
# -------------------------------------------------------------------------


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Capture screenshot on test failure.
    """
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        # Get driver from test item
        driver = item.funcargs.get("driver")
        screenshots_dir = item.funcargs.get("screenshots_dir")

        if driver and screenshots_dir:
            screenshot_name = f"{item.name}_failure.png"
            screenshot_path = os.path.join(screenshots_dir, screenshot_name)
            try:
                driver.save_screenshot(screenshot_path)
                print(f"\nScreenshot saved: {screenshot_path}")
            except Exception as e:
                print(f"\nFailed to capture screenshot: {e}")
