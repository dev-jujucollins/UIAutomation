"""Tests for calendar onboarding."""

from unittest.mock import MagicMock

from uiautomation.pages.calendar.calendar_onboarding import CalendarOnboardingPage


def test_dismiss_location_permission_uses_dont_allow() -> None:
    """Location dismissal should decline permission instead of granting it."""
    page = CalendarOnboardingPage(MagicMock())
    page.is_location_permission_showing = MagicMock(return_value=True)
    page.is_element_present = MagicMock(return_value=True)
    page.click = MagicMock()

    assert page.dismiss_location_permission() is True
    page.click.assert_called_once_with(page.DONT_ALLOW_BUTTON)


def test_dismiss_all_onboarding_fails_when_prompt_cannot_be_cleared() -> None:
    """Visible onboarding that cannot be handled should fail closed."""
    page = CalendarOnboardingPage(MagicMock())
    page.is_location_permission_showing = MagicMock(return_value=True)
    page.dismiss_location_permission = MagicMock(return_value=False)
    page.is_notifications_permission_showing = MagicMock(return_value=False)
    page.is_element_present = MagicMock(return_value=False)

    assert page.dismiss_all_onboarding(max_screens=1) is False
