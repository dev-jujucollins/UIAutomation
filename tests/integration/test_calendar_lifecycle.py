"""Opt-in create/reopen/edit/delete journey with UUID-owned simulator events."""

from dataclasses import dataclass
from uuid import uuid4

import pytest

from uiautomation.pages.calendar.events import CalendarEventsPage

pytestmark = [pytest.mark.calendar, pytest.mark.lifecycle, pytest.mark.journey]


@dataclass(frozen=True)
class OwnedCalendarEvent:
    """Names registered with cleanup before any event is created."""

    page: CalendarEventsPage
    original: str
    edited: str


@pytest.fixture
def owned_calendar_event(
    lifecycle_simulator: None, request: pytest.FixtureRequest
) -> OwnedCalendarEvent:
    """Enter the app only after opt-in checks, then register both possible persisted titles."""
    home = request.getfixturevalue("calendar_home")
    original = f"UIAutomation Event {uuid4().hex}"
    edited = f"{original} edited"
    page = CalendarEventsPage(home.driver, (original, edited))
    request.addfinalizer(page.cleanup)
    return OwnedCalendarEvent(page, original, edited)


def test_calendar_event_lifecycle(owned_calendar_event: OwnedCalendarEvent) -> None:
    """Persist, reopen, rename, reopen again, delete, and verify owned event absence."""
    page = owned_calendar_event.page
    original, edited = owned_calendar_event.original, owned_calendar_event.edited
    page.create_all_day(original)
    page.relaunch()
    page.open_event(original)
    page.rename_event(original, edited)
    page.relaunch()
    page.open_event(edited)
    page.delete_event(edited)
    page.relaunch()
    page.assert_absent(original)
    page.assert_absent(edited)
