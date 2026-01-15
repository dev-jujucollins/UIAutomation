"""Calendars List Page object for iOS Calendar app automation."""

from typing import List, Optional

from ..base_page import BasePage


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

    def tap_done(self) -> "CalendarHomePage":
        """
        Close the Calendars list and return to calendar home.

        Returns:
            CalendarHomePage instance.
        """
        import time

        from selenium.common.exceptions import StaleElementReferenceException

        from .calendar_home import CalendarHomePage

        # Retry logic for stale element issues
        for attempt in range(3):
            try:
                self.click(self.DONE_BUTTON)
                break
            except StaleElementReferenceException:
                if attempt < 2:
                    time.sleep(0.5)
                else:
                    raise

        return CalendarHomePage(self.driver)

    def get_calendar_names(self) -> List[str]:
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
                if label:
                    # Label format: "CalendarName" or "CalendarName, Shared by..."
                    name = label.split(",")[0].strip()
                    if name:
                        calendars.append(name)
            except Exception:
                continue

        return calendars

    def get_account_names(self) -> List[str]:
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
                if name and "@" in name and "calendarlist-cell" not in name:
                    accounts.append(name)
            except Exception:
                continue

        return accounts

    def tap_calendar(self, calendar_name: str) -> None:
        """
        Tap a calendar to toggle its visibility.

        Args:
            calendar_name: Name of the calendar to tap.
        """
        # Try to find by label containing calendar name
        calendar_locator = (
            BasePage.By.IOS_PREDICATE,
            f"type == 'XCUIElementTypeCell' AND label CONTAINS '{calendar_name}'",
        )
        if self.is_element_present(calendar_locator, timeout=3):
            self.click(calendar_locator)

    def is_calendar_selected(self, calendar_name: str) -> bool:
        """
        Check if a calendar is selected (visible in main view).

        Args:
            calendar_name: Name of the calendar.

        Returns:
            True if calendar is selected.
        """
        # Selected calendars have "checkmark.circle.fill" image
        calendar_locator = (
            BasePage.By.IOS_PREDICATE,
            f"type == 'XCUIElementTypeCell' AND label CONTAINS '{calendar_name}'",
        )
        if self.is_element_present(calendar_locator, timeout=3):
            cell = self.find_element(calendar_locator)
            # Check for checkmark image
            try:
                cell.find_element(
                    BasePage.By.IOS_PREDICATE,
                    "name == 'checkmark.circle.fill'",
                )
                return True
            except Exception:
                return False
        return False

    def select_calendar(self, calendar_name: str) -> None:
        """
        Select a calendar if not already selected.

        Args:
            calendar_name: Name of the calendar to select.
        """
        if not self.is_calendar_selected(calendar_name):
            self.tap_calendar(calendar_name)

    def deselect_calendar(self, calendar_name: str) -> None:
        """
        Deselect a calendar if currently selected.

        Args:
            calendar_name: Name of the calendar to deselect.
        """
        if self.is_calendar_selected(calendar_name):
            self.tap_calendar(calendar_name)

    def tap_calendar_info(self, calendar_name: str) -> None:
        """
        Tap the info button for a calendar.

        Args:
            calendar_name: Name of the calendar.
        """
        # Find the cell and then tap the info button within it
        calendar_locator = (
            BasePage.By.IOS_PREDICATE,
            f"type == 'XCUIElementTypeCell' AND label CONTAINS '{calendar_name}'",
        )
        if self.is_element_present(calendar_locator, timeout=3):
            cell = self.find_element(calendar_locator)
            try:
                info_button = cell.find_element(
                    BasePage.By.IOS_PREDICATE,
                    "name == 'info.circle'",
                )
                info_button.click()
            except Exception:
                pass

    def expand_account(self, account_email: str) -> None:
        """
        Expand an account section to show its calendars.

        Args:
            account_email: Email address of the account.
        """
        account_locator = (BasePage.By.ACCESSIBILITY_ID, account_email)
        if self.is_element_present(account_locator, timeout=3):
            self.click(account_locator)
