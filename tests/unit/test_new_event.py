"""Regression tests for Calendar's collapsible date controls."""

from unittest.mock import MagicMock

import pytest
from selenium.common.exceptions import TimeoutException

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
