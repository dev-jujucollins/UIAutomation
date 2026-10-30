"""Report every renamed control on each app's main screens in one pass."""

import pytest
from appium.webdriver.webdriver import WebDriver

from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.pages.base_page import BasePage
from uiautomation.pages.calendar.calendar_home import CalendarHomePage
from uiautomation.pages.calendar.new_event import NewEventPage
from uiautomation.pages.contacts import ContactsPage
from uiautomation.pages.maps import MapsPage
from uiautomation.pages.messages.compose_message import ComposeMessagePage
from uiautomation.pages.messages.messages_home import MessagesHomePage
from uiautomation.pages.settings import SettingsHomePage

pytestmark = [pytest.mark.diagnostic, pytest.mark.locators]


def assert_locators_found(page: BasePage) -> None:
    """Fail with every missing locator, not just the first."""
    missing = page.missing_health_locators()
    assert not missing, "Locators matched nothing:\n  " + "\n  ".join(missing)


@pytest.mark.settings
def test_settings_home_locators(settings_app: SettingsHomePage) -> None:
    assert_locators_found(settings_app)


@pytest.mark.calendar
def test_calendar_home_locators(calendar_home: CalendarHomePage) -> None:
    assert_locators_found(calendar_home)


@pytest.mark.calendar
def test_calendar_editor_locators(calendar_draft: NewEventPage) -> None:
    assert_locators_found(calendar_draft)


@pytest.mark.messages
def test_messages_home_locators(messages_home: MessagesHomePage) -> None:
    assert_locators_found(messages_home)


@pytest.mark.messages
def test_messages_compose_locators(message_draft: ComposeMessagePage) -> None:
    assert_locators_found(message_draft)


@pytest.mark.contacts
def test_contacts_list_locators(request: pytest.FixtureRequest, driver: WebDriver) -> None:
    page = ContactsPage(driver)
    request.addfinalizer(lambda: page.launcher.terminate(SystemApps.CONTACTS))
    page.relaunch()
    page.wait_until_ready()
    assert_locators_found(page)


@pytest.mark.maps
def test_maps_home_locators(maps_home: MapsPage) -> None:
    assert_locators_found(maps_home)
