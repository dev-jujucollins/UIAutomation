"""Calendars List Page object for iOS Calendar app automation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from ...utils.locators import predicate_literal
from ..base_page import BasePage

if TYPE_CHECKING:
    from .calendar_home import CalendarHomePage


class CalendarsListPage(BasePage):
    """
    Page object for the Calendar app Calendars list screen.

    Provides methods to view and manage calendar subscriptions.
    """

    # Locators - iOS 26.3 compatible
    # Navigation
    DONE_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "done-button")
    CALENDARS_TITLE = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeStaticText' AND name == 'Calendars'",
    )

    # Calendar cells - iOS 26.3 uses "calendarlist-cell:account:calendar" naming
    CALENDAR_CELLS = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeCell' AND name CONTAINS 'calendarlist-cell'",
    )

    # Account header cells
    ACCOUNT_CELLS = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeCell' AND name CONTAINS '@'",
    )

    def is_on_calendars_list(self) -> bool:
        """
        Check if currently on Calendars list page.

        Returns:
            True if on Calendars list.
        """
        return self.is_element_visible(self.CALENDARS_TITLE)

    def tap_done(self) -> CalendarHomePage:
        """
        Close the Calendars list and return to calendar home.

        Returns:
            CalendarHomePage instance.
        """
        from .calendar_home import CalendarHomePage

        def close(driver: WebDriver) -> bool:
            try:
                button = driver.find_element(*self.DONE_BUTTON)
                if not button.is_displayed() or not button.is_enabled():
                    return False
            except StaleElementReferenceException:
                return False
            try:
                button.click()
            except StaleElementReferenceException:
                # A successful tap can dismiss the sheet before the response.
                # Confirm dismissal below instead of tapping again.
                pass
            return True

        self._get_wait(None).until(close)
        self.wait_for_invisible(self.CALENDARS_TITLE)
        return CalendarHomePage(self.driver)

    def get_calendar_names(self) -> list[str]:
        """
        Get list of all calendar names.

        Returns:
            List of calendar names.
        """
        calendars = []
        cells = self.find_elements(self.CALENDAR_CELLS, timeout=5)

        for cell in cells:
            try:
                label = cell.get_attribute("label")
                if isinstance(label, str):
                    # Label format: "CalendarName" or "CalendarName, Shared by..."
                    name = label.split(",")[0].strip()
                    if name:
                        calendars.append(name)
            except StaleElementReferenceException:
                continue

        return calendars

    def get_account_names(self) -> list[str]:
        """
        Get list of calendar account names (email addresses).

        Returns:
            List of account email addresses.
        """
        accounts = []
        cells = self.find_elements(self.ACCOUNT_CELLS, timeout=5)

        for cell in cells:
            try:
                name = cell.get_attribute("name")
                if isinstance(name, str) and "@" in name and "calendarlist-cell" not in name:
                    accounts.append(name)
            except StaleElementReferenceException:
                continue

        return accounts

    def tap_calendar(self, calendar_name: str) -> None:
        """
        Tap a calendar to toggle its visibility.

        Args:
            calendar_name: Name of the calendar to tap.
        """
        self._set_calendar_selected(calendar_name, not self.is_calendar_selected(calendar_name))

    def _calendar_locator(self, calendar_name: str) -> tuple[str, str]:
        """Match the full name, allowing the cell's optional metadata suffix."""
        return (
            self.By.IOS_PREDICATE,
            "type == 'XCUIElementTypeCell' AND "
            f"(label == {predicate_literal(calendar_name)} OR "
            f"label BEGINSWITH {predicate_literal(calendar_name + ', ')})",
        )

    def _calendar_selected(self, calendar_name: str) -> bool:
        """Read an existing cell; only an absent checkmark means unselected."""
        cell = self.driver.find_element(*self._calendar_locator(calendar_name))
        try:
            cell.find_element(self.By.IOS_PREDICATE, "name == 'checkmark.circle.fill'")
        except NoSuchElementException:
            return False
        return True

    def _set_calendar_selected(self, calendar_name: str, selected: bool) -> None:
        """Require the named calendar, then wait for the requested selection."""
        if self.is_calendar_selected(calendar_name) != selected:
            self.click(self._calendar_locator(calendar_name))

        def ready(_: WebDriver) -> bool:
            try:
                return self._calendar_selected(calendar_name) == selected
            except StaleElementReferenceException:
                return False

        self._get_wait(None).until(
            ready, message=f"Calendar {calendar_name!r} did not reach selected={selected}"
        )

    def is_calendar_selected(self, calendar_name: str) -> bool:
        """
        Check if a calendar is selected (visible in main view).

        Args:
            calendar_name: Name of the calendar.

        Returns:
            True if calendar is selected.
        """
        result = False

        def readable(_: WebDriver) -> bool:
            nonlocal result
            try:
                result = self._calendar_selected(calendar_name)
                return True
            except StaleElementReferenceException:
                return False

        self._get_wait(None).until(readable, message=f"Calendar {calendar_name!r} is unavailable")
        return result

    def select_calendar(self, calendar_name: str) -> None:
        """
        Select a calendar if not already selected.

        Args:
            calendar_name: Name of the calendar to select.
        """
        self._set_calendar_selected(calendar_name, True)

    def deselect_calendar(self, calendar_name: str) -> None:
        """
        Deselect a calendar if currently selected.

        Args:
            calendar_name: Name of the calendar to deselect.
        """
        self._set_calendar_selected(calendar_name, False)

    def tap_calendar_info(self, calendar_name: str) -> None:
        """
        Tap the info button for a calendar.

        Args:
            calendar_name: Name of the calendar.
        """
        cell = self.find_element(self._calendar_locator(calendar_name))
        cell.find_element(self.By.IOS_PREDICATE, "name == 'info.circle'").click()

    def expand_account(self, account_email: str) -> None:
        """
        Expand an account section to show its calendars.

        Args:
            account_email: Email address of the account.
        """
        account_locator = (BasePage.By.ACCESSIBILITY_ID, account_email)
        self.click(account_locator)
