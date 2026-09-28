"""Stateful contracts for owned Calendar data and recovery after partial failures."""

from collections.abc import Callable
from unittest.mock import MagicMock, call, patch

import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.wait import WebDriverWait

from uiautomation.pages.base_page import BasePage
from uiautomation.pages.calendar.calendar_onboarding import CalendarOnboardingPage
from uiautomation.pages.calendar.events import CalendarEventsPage
from uiautomation.pages.calendar.new_event import NewEventPage


class CalendarHarness:
    """Small UI model: an event survives closing, editing, and reopening its sheets."""

    def __init__(self) -> None:
        self.driver = MagicMock()
        self.state = "home"
        self.events: set[str] = set()
        self.current = ""
        self.draft = ""
        self.all_day = False
        self.collapsed = True
        self.discard_destination = "home"
        self.deleted: list[str] = []
        self.notifications_after_save = False
        self.wrong_detail = False
        self.driver.find_elements.side_effect = self.find
        self.driver.find_element.side_effect = self.find_one
        self.driver.execute_script.return_value = "2026-09-27"

    def element(
        self,
        name: str,
        click: Callable[[], None] | None = None,
        *,
        label: str | None = None,
        visible: bool = True,
        value: Callable[[], str] | None = None,
    ) -> MagicMock:
        element = MagicMock()
        element.id = f"{self.state}:{name}"
        element.is_displayed.return_value = visible
        element.is_enabled.return_value = True
        element.get_attribute.side_effect = lambda attribute: (
            value() if attribute == "value" and value else label if attribute == "label" else name
        )
        if click:
            element.click.side_effect = click
        return element

    def switch_state(self, state: str) -> None:
        self.state = state

    def open_new(self) -> None:
        self.state, self.draft, self.all_day, self.collapsed = "new", "", False, True

    def open_event(self, title: str) -> None:
        self.current = "Other person's event" if self.wrong_detail else title
        self.state = "detail"

    def edit(self) -> None:
        self.state, self.draft, self.all_day, self.collapsed = "edit", self.current, True, True

    def cancel_editor(self) -> None:
        self.discard_destination = "detail" if self.state == "edit" else "home"
        self.state = "discard_sheet" if self.draft else self.discard_destination

    def save(self) -> None:
        if self.state == "edit":
            self.events.remove(self.current)
            self.events.add(self.draft)
            self.current, self.state = self.draft, "detail"
        else:
            assert self.all_day, "The lifecycle must persist an all-day event"
            self.events.add(self.draft)
            self.state = "notifications" if self.notifications_after_save else "home"

    def delete(self) -> None:
        self.events.remove(self.current)
        self.deleted.append(self.current)
        self.state = "home"

    def find_one(self, by: str, value: str) -> MagicMock:
        matches = self.find(by, value)
        if not matches:
            raise NoSuchElementException(value)
        return matches[0]

    def find(self, by: str, value: str) -> list[MagicMock]:
        locator = by, value
        page = CalendarEventsPage
        if self.state == "home":
            if locator in (page.DAY_VIEW_NAV_BAR, page.MONTH_VIEW_NAV_BAR):
                return [self.element(value)] if locator == page.DAY_VIEW_NAV_BAR else []
            if locator == page.TODAY_BUTTON:
                return [self.element(value)]
            if locator == page.ADD_BUTTON:
                return [self.element(value, self.open_new)]
            if locator == page.CURRENT_DAY_LABEL:
                return [self.element(value, label="Sunday – Sep 27, 2026")]
            if (
                value.startswith("event-shown:")
                and value.removeprefix("event-shown:") in self.events
            ):
                title = value.removeprefix("event-shown:")
                return [self.element(value, lambda: self.open_event(title))]
        if self.state in ("new", "edit", "discard_sheet"):
            if locator == NewEventPage.TITLE_FIELD:
                field = self.element(
                    "title-field", visible=self.state != "discard_sheet", value=lambda: self.draft
                )
                field.clear.side_effect = lambda: setattr(self, "draft", "")
                field.send_keys.side_effect = lambda text: setattr(self, "draft", text)
                return [field]
            if locator == NewEventPage.CANCEL_BUTTON and self.state != "discard_sheet":
                return [self.element("Cancel", self.cancel_editor)]
            if locator == NewEventPage.ADD_DONE_BUTTON and self.state != "discard_sheet":
                return [self.element("Done", self.save)]
            if locator == NewEventPage.COLLAPSED_DATE_TIME and self.collapsed:
                return [self.element(value, lambda: setattr(self, "collapsed", False))]
            if locator == NewEventPage.ALL_DAY_SWITCH and not self.collapsed:
                switch = self.element(value, value=lambda: "1" if self.all_day else "0")
                toggle = self.element("inner", lambda: setattr(self, "all_day", not self.all_day))
                switch.find_elements.return_value = [toggle]
                return [switch]
            if value == "Discard Changes" and self.state == "discard_sheet":
                return [self.element(value, lambda: self.switch_state(self.discard_destination))]
        if self.state == "detail":
            if locator == page.DETAILS_TITLE:
                return [self.element(value, label=self.current)]
            if locator == page.DETAIL_CLOSE:
                return [self.element(value, lambda: self.switch_state("home"))]
            if locator == page.EDIT_BUTTON:
                return [self.element(value, self.edit)]
            if locator == page.DELETE_BUTTON:
                return [self.element(value, lambda: self.switch_state("delete_sheet"))]
        if self.state == "delete_sheet" and locator == page.DELETE_SHEET:
            sheet = self.element("delete-sheet")
            confirm = self.element("delete-alert-button", self.delete, visible=False)
            sheet.find_element.side_effect = lambda *nested: (
                confirm if nested == page.DELETE_CONFIRM else self.find_one(*nested)
            )
            return [sheet]
        if self.state == "notifications":
            if locator == CalendarOnboardingPage.NOTIFICATIONS_ALERT:
                return [self.element("notifications")]
            if locator == CalendarOnboardingPage.DONT_ALLOW_BUTTON:
                return [self.element("Don't Allow", lambda: self.switch_state("home"))]
        if locator == (BasePage.By.CLASS_NAME, "XCUIElementTypeSheet") and self.state.endswith(
            "sheet"
        ):
            return [self.element(self.state)]
        if (
            locator == (BasePage.By.CLASS_NAME, "XCUIElementTypeAlert")
            and self.state == "notifications"
        ):
            return [self.element(self.state)]
        return []


@pytest.fixture
def calendar(monkeypatch: pytest.MonkeyPatch) -> tuple[CalendarHarness, CalendarEventsPage]:
    monkeypatch.setattr(
        BasePage,
        "_get_wait",
        lambda self, timeout: WebDriverWait(self.driver, 0.5, poll_frequency=0.001),
    )
    harness = CalendarHarness()
    return harness, CalendarEventsPage(harness.driver, ("Owned original", "Owned edited"))


def test_all_day_event_is_reopened_edited_reopened_and_deleted(calendar) -> None:
    harness, page = calendar
    harness.notifications_after_save = True
    page.create_all_day("Owned original")
    page.open_event("Owned original")
    page.rename_event("Owned original", "Owned edited")
    page.open_event("Owned edited")
    page.delete_event("Owned edited")
    page.assert_absent("Owned original")
    page.assert_absent("Owned edited")
    assert harness.events == set()
    assert harness.deleted == ["Owned edited"]


@pytest.mark.parametrize(
    "method", ["create_all_day", "open_event", "delete_event", "assert_absent"]
)
def test_unowned_titles_are_rejected_without_data_mutation(calendar, method: str) -> None:
    harness, page = calendar
    harness.events.add("Other person's event")
    with pytest.raises(ValueError, match="not owned"):
        getattr(page, method)("Other person's event")
    assert harness.events == {"Other person's event"}
    assert harness.deleted == []


def test_rename_requires_replacement_title_to_be_registered(calendar) -> None:
    harness, page = calendar
    with pytest.raises(ValueError, match="not owned"):
        page.rename_event("Owned original", "unregistered replacement")
    assert harness.state == "home"


def test_delete_rechecks_detail_identity_before_showing_confirmation(calendar) -> None:
    harness, page = calendar
    harness.events.add("Owned original")
    harness.wrong_detail = True
    with pytest.raises(TimeoutException):
        page.delete_event("Owned original")
    assert harness.events == {"Owned original"}
    assert harness.deleted == []
    assert page._pending_delete is None


def test_duplicate_owned_title_is_not_created_twice(calendar) -> None:
    harness, page = calendar
    harness.events.add("Owned original")
    with pytest.raises(AssertionError, match="already exists"):
        page.create_all_day("Owned original")
    assert harness.events == {"Owned original"}


@pytest.mark.parametrize(
    "failure_stage", ["new_draft", "saved", "edit_draft", "renamed", "confirm_delete"]
)
def test_cleanup_recovers_partial_failures_and_preserves_unrelated_events(
    calendar, failure_stage: str
) -> None:
    harness, page = calendar
    harness.events.add("Unrelated")
    if failure_stage == "new_draft":
        harness.open_new()
        harness.draft = "Owned original"
    else:
        page.create_all_day("Owned original")
        if failure_stage == "edit_draft":
            page.open_event("Owned original")
            harness.edit()
            harness.draft = "Owned edited"
        elif failure_stage == "renamed":
            page.rename_event("Owned original", "Owned edited")
            page.open_event("Owned edited")
        elif failure_stage == "confirm_delete":
            page.open_event("Owned original")
            page._pending_delete = "Owned original"
            harness.state = "delete_sheet"
    page.cleanup()
    assert harness.events == {"Unrelated"}
    assert harness.state == "home"


def test_cleanup_never_confirms_an_unowned_deletion_sheet(calendar) -> None:
    harness, page = calendar
    harness.state, harness.current = "delete_sheet", "Unrelated"
    harness.events.add("Unrelated")
    with pytest.raises(AssertionError, match="unowned"):
        page.cleanup()
    assert harness.events == {"Unrelated"}


def test_absence_check_fails_while_the_owned_event_still_exists(calendar) -> None:
    harness, page = calendar
    harness.events.add("Owned original")
    with pytest.raises(TimeoutException):
        page.assert_absent("Owned original")


def test_relaunch_restores_home_around_app_restart(calendar) -> None:
    from uiautomation.drivers.ios_driver import SystemApps

    _, page = calendar
    actions = MagicMock()
    page.close_to_home = actions.home
    page.tap_today = actions.today
    with patch("uiautomation.pages.calendar.events.AppLauncher", return_value=actions):
        page.relaunch()
    assert actions.mock_calls == [
        call.home(),
        call.terminate(SystemApps.CALENDAR),
        call.launch(SystemApps.CALENDAR),
        call.home(),
        call.today(),
    ]
