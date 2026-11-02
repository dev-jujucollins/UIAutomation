"""Report every visible control VoiceOver cannot name, on each app's main screens."""

import pytest
from appium.webdriver.webdriver import WebDriver

from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.pages.base_page import BasePage
from uiautomation.pages.calendar.calendar_home import CalendarHomePage
from uiautomation.pages.calendar.new_event import NewEventPage
from uiautomation.pages.contacts import ContactsPage
from uiautomation.pages.files import FilesPage
from uiautomation.pages.maps import MapsPage
from uiautomation.pages.messages.compose_message import ComposeMessagePage
from uiautomation.pages.messages.messages_home import MessagesHomePage
from uiautomation.pages.photos import PhotosLibraryPage
from uiautomation.pages.reminders import RemindersHomePage
from uiautomation.pages.safari import SafariPage
from uiautomation.pages.settings import SettingsHomePage

pytestmark = [pytest.mark.diagnostic, pytest.mark.accessibility]

FIXTURE_HOME = SafariPage.text("UIAutomation fixture page")


def assert_labelled(page: BasePage) -> None:
    """Fail with every visible control that has no accessibility label."""
    unlabeled = page.unlabeled_controls()
    assert not unlabeled, "Controls without an accessibility label:\n  " + "\n  ".join(unlabeled)


@pytest.mark.settings
def test_settings_home_labels(settings_app: SettingsHomePage) -> None:
    assert_labelled(settings_app)


@pytest.mark.calendar
def test_calendar_home_labels(calendar_home: CalendarHomePage) -> None:
    assert_labelled(calendar_home)


@pytest.mark.calendar
def test_calendar_editor_labels(calendar_draft: NewEventPage) -> None:
    assert_labelled(calendar_draft)


@pytest.mark.messages
def test_messages_home_labels(messages_home: MessagesHomePage) -> None:
    assert_labelled(messages_home)


@pytest.mark.messages
def test_messages_compose_labels(message_draft: ComposeMessagePage) -> None:
    assert_labelled(message_draft)


@pytest.mark.contacts
def test_contacts_list_labels(request: pytest.FixtureRequest, driver: WebDriver) -> None:
    page = ContactsPage(driver)
    request.addfinalizer(lambda: page.launcher.terminate(SystemApps.CONTACTS))
    page.relaunch()
    page.wait_until_ready()
    assert_labelled(page)


@pytest.mark.maps
def test_maps_home_labels(maps_home: MapsPage) -> None:
    assert_labelled(maps_home)


@pytest.mark.reminders
def test_reminders_overview_labels(reminders_home: RemindersHomePage) -> None:
    assert_labelled(reminders_home)


@pytest.mark.safari
def test_safari_labels(safari_home: SafariPage, fixture_site: str) -> None:
    # Safari reopens its last tab; load a known page so only Safari's chrome is judged.
    safari_home.open_url(fixture_site, FIXTURE_HOME)
    assert_labelled(safari_home)


@pytest.mark.photos
def test_photos_library_labels(photos_library: PhotosLibraryPage) -> None:
    assert_labelled(photos_library)


@pytest.mark.files
def test_files_browser_labels(files_home: FilesPage) -> None:
    assert_labelled(files_home)


@pytest.mark.safari
def test_detector_reports_an_unlabeled_web_button(
    request: pytest.FixtureRequest, safari_home: SafariPage, fixture_site: str
) -> None:
    """The check itself works: an icon-only button with no label is reported, alone."""
    # Leave a labelled page as Safari's last tab, so later Safari checks don't inherit this one.
    request.addfinalizer(lambda: safari_home.open_url(fixture_site, FIXTURE_HOME))
    safari_home.open_url(
        fixture_site + "unlabeled.html", SafariPage.text("Unlabeled control fixture")
    )
    unlabeled = [entry for entry in safari_home.unlabeled_controls() if entry.startswith("Button")]
    assert len(unlabeled) == 1, unlabeled
