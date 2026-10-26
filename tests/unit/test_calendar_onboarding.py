"""Tests for calendar onboarding."""

from unittest.mock import MagicMock, patch

import pytest
from selenium.webdriver.support.wait import WebDriverWait

from uiautomation.pages.calendar.calendar_home import CalendarHomePage
from uiautomation.pages.calendar.calendar_onboarding import CalendarOnboardingPage

LOCATION_TITLE = "Allow “Calendar” to use your location?"
NOTIFICATIONS_TITLE = "“Calendar” Would Like to Send You Notifications"


def _alert(title: str) -> MagicMock:
    alert = MagicMock()
    alert.is_displayed.return_value = True
    alert.get_attribute.return_value = title
    return alert


def _page(*alerts: MagicMock) -> CalendarOnboardingPage:
    driver = MagicMock()
    driver.find_elements.return_value = list(alerts)
    page = CalendarOnboardingPage(driver)
    page._wait = WebDriverWait(driver, 0.02, poll_frequency=0.001)
    return page


def test_dismiss_location_permission_uses_dont_allow() -> None:
    """Location dismissal should decline permission instead of granting it."""
    page = CalendarOnboardingPage(MagicMock())
    page.is_location_permission_showing = MagicMock(return_value=True)
    page.is_element_present = MagicMock(return_value=True)
    page.click = MagicMock()

    assert page.dismiss_location_permission() is True
    page.click.assert_called_once_with(page.DONT_ALLOW_BUTTON)


@pytest.mark.parametrize("title", [LOCATION_TITLE, NOTIFICATIONS_TITLE])
def test_known_permission_alerts_are_declined(title: str) -> None:
    alert = _alert(title)
    page = _page(alert)

    assert page.dismiss_known_prompt() is True
    alert.find_element.return_value.click.assert_called_once()


@pytest.mark.parametrize("title", ["Calendar Would Like to Access Your Contacts", ""])
def test_unknown_alert_fails_instead_of_tapping_through(title: str) -> None:
    alert = _alert(title)
    page = _page(alert)

    with pytest.raises(AssertionError, match="Unexpected Calendar alert"):
        page.dismiss_known_prompt()
    alert.find_element.assert_not_called()


def test_no_visible_alert_is_not_a_dismissal() -> None:
    hidden = _alert(LOCATION_TITLE)
    hidden.is_displayed.return_value = False

    assert _page(hidden).dismiss_known_prompt() is False


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
