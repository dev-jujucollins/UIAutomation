"""Reminders overview, list navigation, discarded drafts, and one owned reminder."""

from uuid import uuid4

import pytest

from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.pages.reminders import NewReminderPage, RemindersHomePage
from uiautomation.utils.app_launcher import AppLauncher

pytestmark = pytest.mark.reminders


@pytest.mark.smoke
def test_reminders_home_is_ready(reminders_home: RemindersHomePage) -> None:
    """Reminders reaches its lists overview past first-launch screens."""
    assert reminders_home.list_count() >= 0


@pytest.mark.journey
def test_open_default_list_and_return(reminders_home: RemindersHomePage) -> None:
    """The default list opens and Back returns to the overview."""
    reminders_list = reminders_home.open_list()
    reminders_list.go_back()


@pytest.mark.journey
def test_discarded_draft_creates_nothing(
    reminders_home: RemindersHomePage, reminder_draft: NewReminderPage
) -> None:
    """A typed then discarded reminder never reaches the list."""
    before = reminders_home.list_count()
    title = f"UIAutomation draft {uuid4().hex[:8]}"
    reminder_draft.set_title(title)
    reminder_draft.discard()
    assert reminders_home.list_count() == before
    assert reminders_home.open_list().state(title) is None


def _relaunch(home: RemindersHomePage) -> RemindersHomePage:
    """Restart Reminders so each check reads persisted data, not the current screen."""
    launcher = AppLauncher(home.driver)
    launcher.terminate(SystemApps.REMINDERS)
    launcher.launch(SystemApps.REMINDERS)
    home.wait_until_ready()
    return home


def _delete_everywhere(home: RemindersHomePage, title: str) -> None:
    """Delete the owned title wherever it is; a completed reminder lives in Completed."""
    _relaunch(home)
    for open_list in (home.open_list, home.open_completed):
        page = open_list()
        if page.state(title) is not None:
            page.delete(title)
        page.go_back()


@pytest.mark.lifecycle
@pytest.mark.regression
def test_reminder_create_complete_delete(
    request: pytest.FixtureRequest, lifecycle_simulator: None
) -> None:
    """A reminder persists across relaunches, moves to Completed, and deletes cleanly."""
    home = request.getfixturevalue("reminders_home")
    title = f"UIAutomation {uuid4().hex[:12]}"
    assert home.open_list().state(title) is None, "Generated title already exists"
    home = _relaunch(home)
    # Register cleanup before creating: only this exact generated title is ever deleted.
    request.addfinalizer(lambda: _delete_everywhere(home, title))

    sheet = home.open_new_reminder()
    sheet.set_title(title)
    sheet.save()

    page = _relaunch(home).open_list()
    assert page.state(title) == "Incomplete", "Created reminder did not survive relaunch"
    page.complete(title)

    completed = _relaunch(home).open_completed()
    assert completed.state(title) == "Completed", "Completed reminder missing after relaunch"
    completed.delete(title)

    home = _relaunch(home)
    assert home.open_list().state(title) is None
    assert _relaunch(home).open_completed().state(title) is None
