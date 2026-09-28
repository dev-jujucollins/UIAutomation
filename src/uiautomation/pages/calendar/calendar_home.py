"""Calendar Home Page object for iOS Calendar app automation."""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING

from ..base_page import BasePage

if TYPE_CHECKING:
    from .calendars_list import CalendarsListPage
    from .new_event import NewEventPage


class CalendarHomePage(BasePage):
    """
    Page object for the Calendar app home screen (Month view).

    Provides methods to interact with the calendar month view,
    navigate between dates, and access calendar features.
    """

    # Locators - iOS 26.3 compatible (Day View is default)
    # Navigation bar elements
    MONTH_VIEW_NAV_BAR = (BasePage.By.ACCESSIBILITY_ID, "MonthViewContainerView")
    DAY_VIEW_NAV_BAR = (BasePage.By.ACCESSIBILITY_ID, "DayViewContainerView")
    BACK_BUTTON = (
        BasePage.By.IOS_CLASS_CHAIN,
        "**/XCUIElementTypeNavigationBar[`name == 'DayViewContainerView'`]/XCUIElementTypeButton[1]",
    )
    TOGGLE_VIEW_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "toggle-day-list-view")
    SEARCH_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "searchbar-button")
    ADD_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "add-plus-button")
    CURRENT_DAY_LABEL = (BasePage.By.ACCESSIBILITY_ID, "current-day")

    # Toolbar buttons
    TODAY_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "today-button")
    CALENDARS_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "calendars-button")
    INBOX_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "inbox-button")
    TOOLBAR = (BasePage.By.ACCESSIBILITY_ID, "Toolbar")

    # Today's date element in the horizontal date picker (has "Today" in name)
    TODAY_DATE_ELEMENT = (
        BasePage.By.IOS_PREDICATE,
        "name CONTAINS 'Today' AND type == 'XCUIElementTypeOther'",
    )

    def is_on_calendar_home(self) -> bool:
        """
        Check if currently on Calendar home page.

        Returns:
            True if on Calendar home (day view in iOS 26.3).
        """
        # iOS 26.3 uses Day View by default - check for toolbar or navigation bar
        return self.is_element_visible(self.TOOLBAR) or self.is_element_visible(
            self.DAY_VIEW_NAV_BAR
        )

    def is_on_month_view(self, timeout: int = BasePage.DEFAULT_TIMEOUT) -> bool:
        """Identify month view by its own navigation bar, not the shared toolbar."""
        return self.is_element_visible(self.MONTH_VIEW_NAV_BAR, timeout=timeout)

    def get_current_month(self) -> str | None:
        """
        Get the currently displayed month name from the current day label.

        Returns:
            Month name (e.g., "January") or None.
        """
        # In iOS 26.3, current-day shows format like "Sunday – Jan 11, 2026"
        if self.is_element_present(self.CURRENT_DAY_LABEL):
            element = self.find_element(self.CURRENT_DAY_LABEL)
            label = element.get_attribute("label")
            if label and isinstance(label, str):
                # Parse month from label like "Sunday – Jan 11, 2026"
                month_abbrevs = {
                    "Jan": "January",
                    "Feb": "February",
                    "Mar": "March",
                    "Apr": "April",
                    "May": "May",
                    "Jun": "June",
                    "Jul": "July",
                    "Aug": "August",
                    "Sep": "September",
                    "Oct": "October",
                    "Nov": "November",
                    "Dec": "December",
                }
                for abbrev, full_name in month_abbrevs.items():
                    if abbrev in label:
                        return full_name
        return None

    def tap_today(self) -> None:
        """Navigate to today's date."""
        self.click(self.TODAY_BUTTON)
        expected = self.get_device_date()
        self._get_wait(None).until(
            lambda _: self.get_selected_date() == expected,
            "Calendar did not navigate to the target's current date",
        )

    def select_another_visible_day(self) -> date:
        """Select an unselected date in the day strip and verify navigation."""
        before = self.get_selected_date()
        locator = (
            self.By.IOS_PREDICATE,
            "type == 'XCUIElementTypeButton' AND name MATCHES "
            "'^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday), [A-Za-z]+ [0-9]+$'",
        )
        candidates = [element for element in self.find_elements(locator) if element.is_displayed()]
        if not candidates:
            raise AssertionError("No alternate date is visible in Calendar's day strip")
        candidates[0].click()
        self._get_wait(None).until(
            lambda _: self.get_selected_date() != before, "Calendar date did not change"
        )
        return self.get_selected_date()

    def tap_back_to_month(self) -> None:
        """
        Tap the Back button to navigate to Month view.

        In iOS 26.3, the Back button is labeled with the current month name
        (e.g., "January") and is located in the top left corner.
        """
        self.click(self.BACK_BUTTON)

    def tap_add_event(self) -> NewEventPage:
        """
        Tap the Add button to create a new event.

        Returns:
            NewEventPage instance.
        """
        from .new_event import NewEventPage

        self.click(self.ADD_BUTTON)
        return NewEventPage(self.driver)

    def tap_calendars(self) -> CalendarsListPage:
        """
        Tap the Calendars button to view calendar list.

        Returns:
            CalendarsListPage instance.
        """
        from .calendars_list import CalendarsListPage

        self.click(self.CALENDARS_BUTTON)
        return CalendarsListPage(self.driver)

    def tap_search(self) -> None:
        """Tap the Search button."""
        self.click(self.SEARCH_BUTTON)

    def tap_toggle_view(self) -> None:
        """Tap the toggle view button to switch between single day and list view."""
        self.click(self.TOGGLE_VIEW_BUTTON)

    def tap_inbox(self) -> None:
        """Tap the Inbox button."""
        self.click(self.INBOX_BUTTON)

    def tap_date(self, date_name: str) -> None:
        """
        Tap a specific date in the calendar.

        Args:
            date_name: The date's accessibility name (e.g., "Monday, January 12").
        """
        date_locator = (BasePage.By.ACCESSIBILITY_ID, date_name)
        self.click(date_locator)

    def get_date_event_count(self, date_name: str) -> str | None:
        """
        Get the event count for a specific date.

        Args:
            date_name: The date's accessibility name.

        Returns:
            Event count string (e.g., "2 events", "No events") or None.
        """
        date_locator = (BasePage.By.ACCESSIBILITY_ID, date_name)
        if self.is_element_present(date_locator, timeout=3):
            element = self.find_element(date_locator)
            value = element.get_attribute("value")
            if isinstance(value, str):
                return value
        return None

    def get_visible_dates_with_events(self) -> list[str]:
        """
        Get list of visible dates that have events.

        Returns:
            List of date names that have events.
        """
        # In iOS 26.3, look for event buttons in day view (event-shown:* prefix)
        dates_with_events = []
        event_buttons = self.find_elements(
            (
                BasePage.By.IOS_PREDICATE,
                "type == 'XCUIElementTypeButton' AND name BEGINSWITH 'event-shown:'",
            )
        )

        for button in event_buttons:
            try:
                name = button.get_attribute("name")
                if name and isinstance(name, str):
                    dates_with_events.append(name)
            except Exception:
                continue

        return dates_with_events

    def scroll_to_next_month(self) -> None:
        """Scroll down to view the next month."""
        self.scroll_down()

    def scroll_to_previous_month(self) -> None:
        """Scroll up to view the previous month."""
        self.scroll_up()

    def is_today_selected(self) -> bool:
        """Compare the selected day with the device's local date."""
        return self.get_selected_date() == self.get_device_date()

    def get_device_date(self) -> date:
        """Read Appium's target date; simulators use the server's clock/timezone."""
        value = self.driver.execute_script("mobile: getDeviceTime", {"format": "YYYY-MM-DD"})
        if not isinstance(value, str):
            raise ValueError(f"Unexpected device date: {value!r}")
        return date.fromisoformat(value)

    @staticmethod
    def parse_selected_date(label: str) -> date:
        """Parse the English current-day label, rejecting incomplete dates."""
        months = (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        )
        for number, month in enumerate(months, start=1):
            match = re.search(rf"\b(?:{month}|{month[:3]})\s+(\d{{1,2}}),?\s+(\d{{4}})\b", label)
            if match:
                return date(int(match[2]), number, int(match[1]))
        raise ValueError(f"Unrecognized Calendar date label: {label!r}")

    def get_selected_date(self) -> date:
        """Read the displayed day rather than presence of a Today control."""
        label = self.get_attribute(self.CURRENT_DAY_LABEL, "label")
        if label is None:
            raise ValueError("Calendar current-day control has no date label")
        return self.parse_selected_date(label)
