"""Tests for calendar onboarding."""

from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait

from uiautomation.pages.calendar.calendar_home import CalendarHomePage
from uiautomation.pages.calendar.calendar_onboarding import CalendarOnboardingPage

LOCATION_TITLE = "Allow “Calendar” to use your location?"
NOTIFICATIONS_TITLE = "“Calendar” Would Like to Send You Notifications"
CONTACTS_TITLE = "Allow “Calendar” to access your contacts?"


def _alert(title: str) -> MagicMock:
    alert = MagicMock()
    alert.is_displayed.return_value = True
    alert.get_attribute.return_value = title
    deny = MagicMock()
    deny.get_attribute.return_value = "Don’t Allow"
    alert.find_elements.return_value = [deny]
    return alert


def _page(*alerts: MagicMock) -> CalendarOnboardingPage:
    driver = MagicMock()
    driver.find_elements.return_value = list(alerts)
    driver.find_element.side_effect = NoSuchElementException()
    page = CalendarOnboardingPage(driver)
    page._wait = WebDriverWait(driver, 0.02, poll_frequency=0.001)
    return page


@pytest.mark.parametrize("title", [LOCATION_TITLE, NOTIFICATIONS_TITLE, CONTACTS_TITLE])
def test_known_permission_alerts_are_declined(title: str) -> None:
    alert = _alert(title)
    page = _page(alert)

    assert page.dismiss_known_prompt() is True
    alert.find_elements.return_value[0].click.assert_called_once_with()


@pytest.mark.parametrize("title", ["Allow “Calendar” to access your photos?", ""])
def test_unknown_alert_fails_instead_of_tapping_through(title: str) -> None:
    alert = _alert(title)
    page = _page(alert)

    with pytest.raises(AssertionError, match="Unexpected Calendar alert"):
        page.dismiss_known_prompt()
    alert.find_elements.return_value[0].click.assert_not_called()


def test_no_visible_alert_is_not_a_dismissal() -> None:
    hidden = _alert(LOCATION_TITLE)
    hidden.is_displayed.return_value = False

    assert _page(hidden).dismiss_known_prompt() is False


def test_whats_new_sheet_is_continued() -> None:
    page = _page()
    page.click = MagicMock()
    with patch.object(
        CalendarOnboardingPage,
        "is_element_visible",
        side_effect=lambda locator, timeout=2: locator == page.WHATS_NEW_TITLE,
    ):
        assert page.dismiss_known_prompt() is True
    page.click.assert_called_once_with(page.WHATS_NEW_CONTINUE)


def test_onboarding_waits_for_prompts_before_home() -> None:
    page = _page()
    page.dismiss_known_prompt = MagicMock(side_effect=[True, False])
    with patch.object(CalendarHomePage, "is_element_visible", return_value=True):
        assert page.dismiss_all_onboarding() is True
    assert page.dismiss_known_prompt.call_count == 2


def test_onboarding_reports_missing_home() -> None:
    page = _page()
    with patch.object(CalendarHomePage, "is_element_visible", return_value=False):
        assert page.dismiss_all_onboarding() is False
