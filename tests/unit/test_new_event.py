"""Regression tests for Calendar's collapsible date controls."""

from unittest.mock import MagicMock

import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait

from uiautomation.pages.calendar.calendar_home import CalendarHomePage
from uiautomation.pages.calendar.new_event import NewEventPage


@pytest.mark.parametrize("collapsed", [True, False])
def test_date_controls_support_collapsed_and_legacy_editors(collapsed: bool) -> None:
    page = NewEventPage(MagicMock())
    page.is_element_visible = MagicMock(return_value=collapsed)
    page.click = MagicMock()
    page.wait_for_visible = MagicMock()

    page.expand_date_time()

    if collapsed:
        page.click.assert_called_once_with(page.COLLAPSED_DATE_TIME)
    else:
        page.click.assert_not_called()
    page.wait_for_visible.assert_called_once_with(page.ALL_DAY_SWITCH)


@pytest.mark.parametrize("value, expected", [("0", False), ("1", True)])
def test_all_day_reads_expanded_control(value: str, expected: bool) -> None:
    page = NewEventPage(MagicMock())
    page.expand_date_time = MagicMock()
    page.find_element = MagicMock()
    page.find_element.return_value.get_attribute.return_value = value

    assert page.is_all_day_enabled() is expected
    page.expand_date_time.assert_called_once_with()


def test_missing_all_day_control_does_not_report_disabled() -> None:
    page = NewEventPage(MagicMock())
    page.expand_date_time = MagicMock(side_effect=TimeoutException())

    with pytest.raises(TimeoutException):
        page.is_all_day_enabled()


@pytest.mark.parametrize("nested", [True, False])
@pytest.mark.parametrize("includes_self", [True, False])
def test_toggle_clicks_nested_control_or_legacy_switch(nested: bool, includes_self: bool) -> None:
    page = NewEventPage(MagicMock())
    actions = MagicMock()
    page.expand_date_time = actions.expand
    page.find_element = actions.find
    switch = actions.find.return_value
    toggle = MagicMock()
    switch.find_elements.return_value = ([switch] if includes_self else []) + (
        [toggle] if nested else []
    )

    page.toggle_all_day()

    assert [call[0] for call in actions.mock_calls[:2]] == ["expand", "find"]
    if nested:
        toggle.click.assert_called_once_with()
        switch.click.assert_not_called()
    else:
        switch.click.assert_called_once_with()


def test_title_input_requires_matching_value() -> None:
    page = NewEventPage(MagicMock())
    page.send_keys = MagicMock()
    page.get_title = MagicMock(return_value="wrong")
    page._wait = WebDriverWait(page.driver, 0)
    with pytest.raises(TimeoutException):
        page.set_title("expected")


@pytest.mark.parametrize("title_visible", [True, False])
def test_discard_handles_delayed_confirmation_and_offscreen_title(title_visible: bool) -> None:
    driver, title, cancel, confirm, home = [MagicMock() for _ in range(5)]
    page = NewEventPage(driver)
    page._wait = WebDriverWait(driver, 0.05, poll_frequency=0.001)
    state = "editor"
    polls = 0
    actions: list[str] = []
    cancel.id, confirm.id = "editor-cancel", "discard-changes"
    title.is_displayed.return_value = title_visible
    cancel.is_displayed.return_value = True
    confirm.is_displayed.return_value = True
    home.is_displayed.return_value = True

    def cancel_editor() -> None:
        nonlocal state
        actions.append("cancel")
        state = "waiting"

    def discard_changes() -> None:
        nonlocal state
        actions.append("discard")
        state = "home"

    def find(by: str, value: str) -> list[MagicMock]:
        nonlocal polls
        locator = by, value
        if value == "Discard Changes" and state == "waiting":
            polls += 1
            return [confirm] if polls >= 3 else []
        if locator == page.TITLE_FIELD and state != "home":
            return [title]
        if locator == page.CANCEL_BUTTON and state == "editor":
            return [cancel]
        if state == "home" and locator in (
            CalendarHomePage.DAY_VIEW_NAV_BAR,
            CalendarHomePage.TODAY_BUTTON,
            CalendarHomePage.ADD_BUTTON,
        ):
            return [home]
        return []

    driver.find_elements.side_effect = find
    cancel.click.side_effect = cancel_editor
    confirm.click.side_effect = discard_changes
    page.discard()
    assert actions == ["cancel", "discard"]
    assert state == "home"


def test_closed_editor_cleanup_does_not_click_unrelated_cancel_button() -> None:
    driver, home, cancel = MagicMock(), MagicMock(), MagicMock()
    page = NewEventPage(driver)
    page._wait = WebDriverWait(driver, 0.02, poll_frequency=0.001)
    home.is_displayed.return_value = True
    cancel.is_displayed.return_value = True
    driver.find_elements.side_effect = lambda *locator: (
        [home]
        if locator
        in (
            CalendarHomePage.DAY_VIEW_NAV_BAR,
            CalendarHomePage.TODAY_BUTTON,
            CalendarHomePage.ADD_BUTTON,
        )
        else [cancel]
        if locator == page.CANCEL_BUTTON
        else []
    )
    page.discard()
    cancel.click.assert_not_called()


def test_discard_requires_an_unobstructed_home() -> None:
    driver, visible = MagicMock(), MagicMock()
    visible.is_displayed.return_value = True
    page = NewEventPage(driver)
    page._wait = WebDriverWait(driver, 0.02, poll_frequency=0.001)
    driver.find_elements.side_effect = lambda *locator: (
        [visible]
        if locator
        in (
            CalendarHomePage.DAY_VIEW_NAV_BAR,
            CalendarHomePage.TODAY_BUTTON,
            CalendarHomePage.ADD_BUTTON,
            (page.By.CLASS_NAME, "XCUIElementTypeSheet"),
        )
        else []
    )
    with pytest.raises(TimeoutException, match="home not restored"):
        page.discard()
    visible.click.assert_not_called()


def test_save_locator_includes_observed_existing_event_done_button() -> None:
    assert "name == 'done-button'" in NewEventPage.ADD_DONE_BUTTON[1]
