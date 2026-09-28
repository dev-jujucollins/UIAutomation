"""Calendar actions must target literal names and report failures."""

from unittest.mock import MagicMock

import pytest
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support.wait import WebDriverWait

from uiautomation.pages.calendar.calendars_list import CalendarsListPage


def quick_page(driver: MagicMock) -> CalendarsListPage:
    driver.find_element.return_value.is_displayed.return_value = True
    driver.find_element.return_value.is_enabled.return_value = True
    page = CalendarsListPage(driver)
    page._wait = WebDriverWait(driver, 0.02, poll_frequency=0.001)
    return page


def test_calendar_locator_escapes_names_and_disambiguates_prefixes() -> None:
    locator = CalendarsListPage(MagicMock())._calendar_locator("Julius's\\Work")
    assert "label == 'Julius\\'s\\\\Work'" in locator[1]
    assert "label BEGINSWITH 'Julius\\'s\\\\Work, '" in locator[1]
    assert "CONTAINS" not in locator[1]


@pytest.mark.parametrize("method", ["tap_calendar", "select_calendar", "deselect_calendar"])
def test_required_calendar_actions_fail_when_calendar_is_missing(method: str) -> None:
    driver = MagicMock()
    driver.find_element.side_effect = NoSuchElementException("missing calendar")
    with pytest.raises(TimeoutException, match="unavailable"):
        getattr(quick_page(driver), method)("Missing")


def test_missing_calendar_info_button_is_not_silently_ignored() -> None:
    driver, cell = MagicMock(), MagicMock()
    driver.find_element.return_value = cell
    cell.find_element.side_effect = NoSuchElementException("missing info button")
    with pytest.raises(NoSuchElementException, match="missing info"):
        quick_page(driver).tap_calendar_info("Work")


def test_selection_does_not_swallow_device_errors() -> None:
    driver, cell = MagicMock(), MagicMock()
    driver.find_element.return_value = cell
    cell.find_element.side_effect = WebDriverException("connection lost")
    with pytest.raises(WebDriverException, match="connection lost"):
        quick_page(driver).is_calendar_selected("Work")


def test_select_calendar_waits_through_stale_and_delayed_checkmarks() -> None:
    driver, cell = MagicMock(), MagicMock()
    driver.find_element.return_value = cell
    cell.find_element.side_effect = [
        NoSuchElementException(),
        StaleElementReferenceException(),
        NoSuchElementException(),
        MagicMock(),
    ]
    quick_page(driver).select_calendar("Work")
    cell.click.assert_called_once()
    assert cell.find_element.call_count == 4


def test_select_calendar_already_selected_does_not_toggle_it() -> None:
    driver, cell = MagicMock(), MagicMock()
    driver.find_element.return_value = cell
    quick_page(driver).select_calendar("Work")
    cell.click.assert_not_called()


def test_select_calendar_fails_if_tap_never_changes_selection() -> None:
    driver, cell = MagicMock(), MagicMock()
    driver.find_element.return_value = cell
    cell.find_element.side_effect = NoSuchElementException()
    with pytest.raises(TimeoutException, match="did not reach selected=True"):
        quick_page(driver).select_calendar("Work")
    cell.click.assert_called_once()


def test_deselect_calendar_requires_the_checkmark_to_disappear() -> None:
    driver, cell = MagicMock(), MagicMock()
    driver.find_element.return_value = cell
    cell.find_element.side_effect = [MagicMock(), MagicMock(), NoSuchElementException()]
    quick_page(driver).deselect_calendar("Work")
    cell.click.assert_called_once()


def test_expand_account_requires_the_requested_control() -> None:
    driver = MagicMock()
    driver.find_element.side_effect = NoSuchElementException()
    with pytest.raises(TimeoutException):
        quick_page(driver).expand_account("missing@example.com")


def test_done_waits_for_dismissal_even_when_the_click_response_is_stale() -> None:
    driver, button, title = MagicMock(), MagicMock(), MagicMock()
    button.is_displayed.return_value = True
    button.is_enabled.return_value = True
    button.click.side_effect = StaleElementReferenceException()
    title.is_displayed.side_effect = [True, False]
    driver.find_element.side_effect = lambda *locator: (
        button if locator == CalendarsListPage.DONE_BUTTON else title
    )
    home = quick_page(driver).tap_done()
    assert home.driver is driver
    button.click.assert_called_once()
    assert title.is_displayed.call_count == 2


def test_done_fails_if_the_sheet_stays_visible() -> None:
    driver, button, title = MagicMock(), MagicMock(), MagicMock()
    button.is_displayed.return_value = True
    button.is_enabled.return_value = True
    title.is_displayed.return_value = True
    driver.find_element.side_effect = lambda *locator: (
        button if locator == CalendarsListPage.DONE_BUTTON else title
    )
    with pytest.raises(TimeoutException):
        quick_page(driver).tap_done()
    button.click.assert_called_once()
