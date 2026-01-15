"""New Event Page object for iOS Calendar app automation."""

from typing import Optional

from ..base_page import BasePage


class NewEventPage(BasePage):
    """
    Page object for the Calendar New Event screen.

    Provides methods to create and edit calendar events.
    """

    # Locators - iOS 26.3 compatible
    # Navigation bar
    CANCEL_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "cancel-button")
    ADD_DONE_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "add-button")
    NEW_TITLE = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeStaticText' AND name == 'New'",
    )

    # Event type segmented control
    EVENT_REMINDER_CONTROL = (BasePage.By.ACCESSIBILITY_ID, "event-reminder-control")
    EVENT_TAB = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND name == 'Event'",
    )
    REMINDER_TAB = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND name == 'Reminder'",
    )

    # Event fields
    TITLE_FIELD = (BasePage.By.ACCESSIBILITY_ID, "title-field")
    LOCATION_FIELD = (BasePage.By.ACCESSIBILITY_ID, "location-video-call-field")

    # All-day switch
    ALL_DAY_SWITCH_CELL = (BasePage.By.ACCESSIBILITY_ID, "all-day-switch-cell")
    ALL_DAY_SWITCH = (BasePage.By.ACCESSIBILITY_ID, "all-day-switch")

    # Date/time pickers
    START_DATE_CELL = (BasePage.By.ACCESSIBILITY_ID, "start-date-picker-cell")
    END_DATE_CELL = (BasePage.By.ACCESSIBILITY_ID, "end-date-picker-cell")
    TRAVEL_TIME_CELL = (BasePage.By.ACCESSIBILITY_ID, "travel-time-cell")

    # Additional options
    REPEAT_CELL = (BasePage.By.ACCESSIBILITY_ID, "repeat-cell")
    CALENDAR_CELL = (BasePage.By.ACCESSIBILITY_ID, "calendar-selection-cell")

    def is_on_new_event_page(self) -> bool:
        """
        Check if currently on New Event page.

        Returns:
            True if on New Event page.
        """
        return self.is_element_visible(self.NEW_TITLE)

    def set_title(self, title: str) -> None:
        """
        Set the event title.

        Args:
            title: Event title text.
        """
        self.send_keys(self.TITLE_FIELD, title, clear_first=True)

    def get_title(self) -> Optional[str]:
        """
        Get the current event title.

        Returns:
            Event title or None.
        """
        if self.is_element_present(self.TITLE_FIELD):
            element = self.find_element(self.TITLE_FIELD)
            return element.get_attribute("value")
        return None

    def tap_location(self) -> None:
        """Tap the location field to enter location."""
        self.click(self.LOCATION_FIELD)

    def is_all_day_enabled(self) -> bool:
        """
        Check if All-day is enabled.

        Returns:
            True if All-day is on.
        """
        if self.is_element_present(self.ALL_DAY_SWITCH):
            element = self.find_element(self.ALL_DAY_SWITCH)
            value = element.get_attribute("value")
            return value == "1"
        return False

    def toggle_all_day(self) -> None:
        """Toggle the All-day switch."""
        self.click(self.ALL_DAY_SWITCH)

    def enable_all_day(self) -> None:
        """Enable All-day if not already enabled."""
        if not self.is_all_day_enabled():
            self.toggle_all_day()

    def disable_all_day(self) -> None:
        """Disable All-day if enabled."""
        if self.is_all_day_enabled():
            self.toggle_all_day()

    def tap_starts(self) -> None:
        """Tap the Starts date picker."""
        self.click(self.START_DATE_CELL)

    def tap_ends(self) -> None:
        """Tap the Ends date picker."""
        self.click(self.END_DATE_CELL)

    def tap_travel_time(self) -> None:
        """Tap Travel Time to set travel time."""
        self.click(self.TRAVEL_TIME_CELL)

    def tap_repeat(self) -> None:
        """Tap Repeat to set recurrence."""
        self.scroll_down()
        self.click(self.REPEAT_CELL)

    def tap_calendar(self) -> None:
        """Tap Calendar to select which calendar to add event to."""
        self.scroll_down()
        self.click(self.CALENDAR_CELL)

    def get_selected_calendar(self) -> Optional[str]:
        """
        Get the currently selected calendar name.

        Returns:
            Calendar name or None.
        """
        if self.is_element_present(self.CALENDAR_CELL, timeout=3):
            element = self.find_element(self.CALENDAR_CELL)
            return element.get_attribute("value")
        return None

    def tap_event_tab(self) -> None:
        """Switch to Event tab."""
        self.click(self.EVENT_TAB)

    def tap_reminder_tab(self) -> None:
        """Switch to Reminder tab."""
        self.click(self.REMINDER_TAB)

    def is_event_tab_selected(self) -> bool:
        """
        Check if Event tab is selected.

        Returns:
            True if Event tab is selected.
        """
        if self.is_element_present(self.EVENT_TAB):
            element = self.find_element(self.EVENT_TAB)
            value = element.get_attribute("value")
            return value == "1"
        return False

    def tap_cancel(self) -> "CalendarHomePage":
        """
        Cancel event creation and return to calendar home.

        Returns:
            CalendarHomePage instance.
        """
        from .calendar_home import CalendarHomePage

        self.click(self.CANCEL_BUTTON)
        return CalendarHomePage(self.driver)

    def tap_done(self) -> "CalendarHomePage":
        """
        Save the event and return to calendar home.

        Returns:
            CalendarHomePage instance.
        """
        from .calendar_home import CalendarHomePage

        self.click(self.ADD_DONE_BUTTON)
        return CalendarHomePage(self.driver)

    def is_done_enabled(self) -> bool:
        """
        Check if the Done button is enabled.

        Returns:
            True if Done is enabled (event can be saved).
        """
        if self.is_element_present(self.ADD_DONE_BUTTON):
            element = self.find_element(self.ADD_DONE_BUTTON)
            return element.is_enabled()
        return False

    def create_simple_event(self, title: str) -> "CalendarHomePage":
        """
        Create a simple event with just a title.

        Args:
            title: Event title.

        Returns:
            CalendarHomePage instance.
        """
        self.set_title(title)
        return self.tap_done()
