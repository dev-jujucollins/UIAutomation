"""
Pytest fixtures for iOS UI Automation tests.
"""

import logging
import subprocess
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from appium.webdriver.webdriver import WebDriver

from uiautomation.drivers.ios_driver import IOSDriver, IOSDriverConfig, SystemApps
from uiautomation.pages.calendar import CalendarHomePage, CalendarOnboardingPage
from uiautomation.pages.maps import MapsPage
from uiautomation.pages.messages import ComposeMessagePage, ConversationPage, MessagesHomePage
from uiautomation.pages.settings import SettingsHomePage, WifiSettingsPage
from uiautomation.utils.app_launcher import AppLauncher
from uiautomation.utils.failure_artifacts import capture_failure
from uiautomation.utils.simulator_control import get_preferred_simulator

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------


RUN_DIRECTORY = pytest.StashKey[Path]()
ACTIVE_DRIVER = pytest.StashKey[WebDriver]()


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration", action="store_true", help="Enable tests using an iOS device"
    )
    parser.addoption(
        "--run-diagnostics", action="store_true", help="Include environment-dependent diagnostics"
    )
    parser.addoption(
        "--restart-simulator",
        action="store_true",
        help="Restart simulator for stuck-runtime recovery",
    )
    parser.addoption(
        "--headless-simulator", action="store_true", help="Boot without opening Device Hub"
    )
    parser.addoption(
        "--artifacts-dir", default="artifacts", help="Root directory for run artifacts"
    )
    parser.addoption(
        "--device-name",
        action="store",
        default=None,
        help="iOS device name (default: best available simulator)",
    )
    parser.addoption(
        "--platform-version",
        action="store",
        default=None,
        help="iOS platform version (default: best available simulator runtime)",
    )
    parser.addoption(
        "--appium-server",
        action="store",
        default="http://localhost:4723",
        help="Appium server URL (default: http://localhost:4723)",
    )
    parser.addoption(
        "--no-reset",
        action="store_true",
        default=False,
        help="Preserve app/device state between driver sessions",
    )
    parser.addoption(
        "--skip-simulator-state-reset",
        action="store_true",
        default=False,
        help="Skip simulator app termination and privacy reset before session start",
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


def pytest_configure(config: pytest.Config) -> None:
    """Assign a unique artifact location without touching the device."""
    if config.getoption("--run-integration") and config.getoption("numprocesses", default=0):
        raise pytest.UsageError(
            "Parallel iOS tests are unsupported: use -n 0; unit tests may use -n auto."
        )
    config.stash[RUN_DIRECTORY] = Path(config.getoption("--artifacts-dir")).resolve() / uuid4().hex


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    """Remember completed driver fixtures even if a dependent fixture fails."""
    outcome = yield
    if fixturedef.argname == "driver" and outcome.excinfo is None:
        request.node.stash[ACTIVE_DRIVER] = outcome.get_result()


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Classify tests and exclude device work unless explicitly enabled."""
    selected, deselected = [], []
    for item in items:
        if "integration" in item.path.parts or "scripts" in item.path.parts:
            item.add_marker(pytest.mark.integration)
        elif "unit" in item.path.parts:
            item.add_marker(pytest.mark.unit)
        required = item.get_closest_marker("real_device")
        if required is not None and config.getoption("--udid") is None:
            reason = required.kwargs.get("reason", "Requires a physical iOS device")
            item.add_marker(pytest.mark.skip(reason=reason))
        if (
            item.get_closest_marker("integration") and not config.getoption("--run-integration")
        ) or (item.get_closest_marker("diagnostic") and not config.getoption("--run-diagnostics")):
            deselected.append(item)
        else:
            selected.append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)


def pytest_collection_finish(session: pytest.Session) -> None:
    """Reject unsafe shared-device parallel runs before fixtures start."""
    if session.config.getoption("numprocesses", default=0) or hasattr(
        session.config, "workerinput"
    ):
        if any(item.get_closest_marker("integration") for item in session.items):
            raise pytest.UsageError(
                "Parallel iOS tests are unsupported: use -n 0; unit tests may use -n auto."
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
    device_name = request.config.getoption("--device-name")
    platform_version = request.config.getoption("--platform-version")

    if udid is None:
        preferred_simulator = get_preferred_simulator(device_name, platform_version)
        device_name = preferred_simulator.name
        platform_version = preferred_simulator.platform_version
    else:
        defaults = IOSDriverConfig()
        device_name = device_name or defaults.device_name
        platform_version = platform_version or defaults.platform_version

    config = IOSDriverConfig(
        device_name=device_name,
        platform_version=platform_version,
        appium_server_url=request.config.getoption("--appium-server"),
        no_reset=request.config.getoption("--no-reset"),
        reset_simulator_state=not request.config.getoption("--skip-simulator-state-reset"),
        restart_simulator=request.config.getoption("--restart-simulator"),
        open_simulator_app=not request.config.getoption("--headless-simulator"),
        appium_log_path=str(request.config.stash[RUN_DIRECTORY] / "appium.log"),
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
    try:
        driver.start()
        yield driver
    finally:
        driver.quit()


@pytest.fixture(scope="function")
def driver(ios_driver: IOSDriver):
    """
    Provide the underlying WebDriver for individual tests.

    App-specific fixtures establish state; this fixture reuses the session.

    Returns:
        Appium WebDriver instance.
    """
    return ios_driver.driver


@pytest.fixture(scope="session")
def is_simulator(request) -> bool:
    """
    Return whether current test target is an iOS simulator.

    Returns:
        True for simulator runs, False for physical devices.
    """
    return request.config.getoption("--udid") is None


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
def settings_app(
    request, driver, app_launcher: AppLauncher
) -> Generator[SettingsHomePage, None, None]:
    """
    Launch Settings app and provide home page object.

    Yields:
        SettingsHomePage instance.
    """
    request.addfinalizer(lambda: app_launcher.terminate(SystemApps.SETTINGS))
    app_launcher.terminate(SystemApps.SETTINGS)
    app_launcher.launch(SystemApps.SETTINGS)
    settings_home = SettingsHomePage(driver)

    # Wait for Settings to be visually ready.
    settings_home.assert_home_visually_ready()

    yield settings_home


@pytest.fixture(scope="function")
def calendar_home(
    request, driver, app_launcher: AppLauncher
) -> Generator[CalendarHomePage, None, None]:
    """
    Launch Calendar app and provide home page object.

    Handles first-time onboarding screens automatically by dismissing
    location permissions and any other intro screens.

    Yields:
        CalendarHomePage instance.
    """
    request.addfinalizer(lambda: app_launcher.terminate(SystemApps.CALENDAR))
    app_launcher.terminate(SystemApps.CALENDAR)
    app_launcher.launch(SystemApps.CALENDAR)

    # Handle onboarding screens (location permission, notifications, etc.)
    onboarding = CalendarOnboardingPage(driver)
    assert onboarding.dismiss_all_onboarding(), "Failed to dismiss Calendar onboarding"

    calendar_page = CalendarHomePage(driver)
    assert calendar_page.is_on_calendar_home(), "Failed to reach Calendar home"

    yield calendar_page


# -------------------------------------------------------------------------
# Utility Fixtures
# -------------------------------------------------------------------------


@pytest.fixture
def messages_home(
    request: pytest.FixtureRequest, driver: WebDriver, app_launcher: AppLauncher
) -> Generator[MessagesHomePage, None, None]:
    """Launch Messages and return to its list without changing existing drafts."""
    request.addfinalizer(lambda: app_launcher.terminate(SystemApps.MESSAGES))
    app_launcher.terminate(SystemApps.MESSAGES)
    app_launcher.launch(SystemApps.MESSAGES)
    conversation = ConversationPage(driver)
    if conversation.is_element_visible(conversation.BACK_BUTTON, timeout=1):
        conversation.go_back()
    home = MessagesHomePage(driver)
    home.wait_until_ready()
    yield home


@pytest.fixture
def message_draft(
    request: pytest.FixtureRequest, messages_home: MessagesHomePage
) -> ComposeMessagePage:
    """Register cleanup before opening a test-owned, unsent compose sheet."""
    page = ComposeMessagePage(messages_home.driver)
    request.addfinalizer(page.discard)
    return messages_home.open_compose()


@pytest.fixture
def restored_wifi(request, settings_app: SettingsHomePage, is_simulator: bool) -> WifiSettingsPage:
    """Restore radio state even when a test or enabling Wi-Fi fails."""
    if is_simulator:
        pytest.skip("Wi-Fi radio controls require physical hardware")
    page = settings_app.go_to_wifi()
    initial_state = page.is_wifi_enabled()

    def restore() -> None:
        if initial_state:
            page.enable_wifi()
        else:
            page.disable_wifi()

    request.addfinalizer(restore)
    return page


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

    if report.failed:
        driver = item.funcargs.get("driver", item.stash.get(ACTIVE_DRIVER, None))
        driver_config = item.funcargs.get("driver_config")
        log_path = (
            Path(driver_config.appium_log_path)
            if driver_config is not None
            else item.config.stash[RUN_DIRECTORY] / "appium.log"
        )
        try:
            destination = capture_failure(
                item.config.stash[RUN_DIRECTORY],
                item.nodeid,
                report.when,
                driver,
                log_path,
                str(report.longrepr),
            )
            report.sections.append(("Failure artifacts", str(destination)))
        except Exception:
            logging.getLogger(__name__).exception("Unable to save failure artifacts")


@pytest.fixture
def maps_home(
    request: pytest.FixtureRequest, is_simulator: bool
) -> Generator[MapsPage, None, None]:
    """Own Maps UI and location permission on a dedicated simulator only."""
    if not is_simulator:
        pytest.skip("Maps coverage requires a dedicated simulator")
    if request.config.getoption("--device-name") != "UIAutomation Maps":
        raise pytest.UsageError("Maps tests require --device-name 'UIAutomation Maps'")
    driver: WebDriver = request.getfixturevalue("driver")
    launcher: AppLauncher = request.getfixturevalue("app_launcher")
    udid = driver.capabilities["udid"]

    def reset_permission() -> None:
        subprocess.run(
            ["xcrun", "simctl", "privacy", udid, "reset", "location", SystemApps.MAPS.value],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    request.addfinalizer(reset_permission)
    request.addfinalizer(lambda: launcher.terminate(SystemApps.MAPS))
    launcher.terminate(SystemApps.MAPS)
    reset_permission()
    launcher.launch(SystemApps.MAPS)
    page = MapsPage(driver)
    permission = getattr(request, "param", "deny")
    if permission not in ("allow", "deny"):
        raise ValueError("Maps permission must be allow or deny")
    page.wait_for_visible((page.By.ACCESSIBILITY_ID, "Allow “Maps” to use your location?"))
    page.wait_until_ready(permission)
    request.addfinalizer(page.close_to_home)
    yield page
