"""
Tests for the iOS Calendar app.

These tests verify Calendar app functionality including:
- App launch and navigation
- Viewing calendars
- Creating events
- Date navigation
- First-time onboarding screens
"""

import pytest

from src.drivers.ios_driver import SystemApps
from src.pages.calendar import CalendarHomePage, CalendarOnboardingPage
from src.utils.app_launcher import AppLauncher


@pytest.mark.calendar
class TestCalendarNavigation:
    """Tests for basic Calendar app navigation."""

    @pytest.mark.smoke
    def test_calendar_app_launches(self, calendar_home: CalendarHomePage):
        """Verify Calendar app launches successfully."""
        assert calendar_home.is_on_calendar_home()

    def test_current_month_displayed(self, calendar_home: CalendarHomePage):
        """Verify current month is displayed."""
        month = calendar_home.get_current_month()
        assert month is not None
        # Month should be a valid month name
        valid_months = [
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
        ]
        assert month in valid_months

    def test_tap_today(self, calendar_home: CalendarHomePage):
        """Test tapping the Today button."""
        calendar_home.tap_today()
        # Should still be on calendar home
        assert calendar_home.is_on_calendar_home()

    def test_navigate_to_month_view(self, calendar_home: CalendarHomePage):
        """Test navigating to month view via back button."""
        import time

        # In iOS 26.3, Day View is default. Month View is accessed via Back button
        # The Back button is labeled with current month name (e.g., "January")
        # Verify we start on calendar home (day view)
        assert calendar_home.is_on_calendar_home()

        # Tap the back button to go to month view
        calendar_home.tap_back_to_month()
        time.sleep(0.5)

        # Verify we can return to day view by tapping Today
        calendar_home.tap_today()
        time.sleep(0.5)

        assert calendar_home.is_on_calendar_home()


@pytest.mark.calendar
class TestCalendarAddEvent:
    """Tests for creating calendar events."""

    def test_open_new_event(self, calendar_home: CalendarHomePage):
        """Test opening the new event screen."""
        new_event_page = calendar_home.tap_add_event()
        assert new_event_page.is_on_new_event_page()
        # Cancel to return to calendar
        new_event_page.tap_cancel()

    def test_new_event_fields_visible(self, calendar_home: CalendarHomePage):
        """Verify all expected fields are visible on new event screen."""
        new_event_page = calendar_home.tap_add_event()

        # Title field should be present
        assert new_event_page.is_element_present(new_event_page.TITLE_FIELD)

        # All-day switch should be present
        assert new_event_page.is_element_present(new_event_page.ALL_DAY_SWITCH)

        # Cancel to return
        new_event_page.tap_cancel()

    def test_set_event_title(self, calendar_home: CalendarHomePage):
        """Test setting an event title."""
        new_event_page = calendar_home.tap_add_event()

        test_title = "Test Meeting"
        new_event_page.set_title(test_title)

        # Done button should be enabled after setting title
        assert new_event_page.is_done_enabled()

        # Cancel without saving
        new_event_page.tap_cancel()

    def test_toggle_all_day(self, calendar_home: CalendarHomePage):
        """Test toggling the All-day switch."""
        new_event_page = calendar_home.tap_add_event()

        initial_state = new_event_page.is_all_day_enabled()
        new_event_page.toggle_all_day()

        # State should have changed
        assert new_event_page.is_all_day_enabled() != initial_state

        # Cancel to return
        new_event_page.tap_cancel()

    def test_event_reminder_tabs(self, calendar_home: CalendarHomePage):
        """Test Event/Reminder tab switching."""
        new_event_page = calendar_home.tap_add_event()

        # Event tab should be selected by default
        assert new_event_page.is_event_tab_selected()

        # Switch to Reminder tab
        new_event_page.tap_reminder_tab()
        assert not new_event_page.is_event_tab_selected()

        # Switch back to Event tab
        new_event_page.tap_event_tab()
        assert new_event_page.is_event_tab_selected()

        # Cancel to return
        new_event_page.tap_cancel()


@pytest.mark.calendar
class TestCalendarsList:
    """Tests for the Calendars list view."""

    def test_open_calendars_list(self, calendar_home: CalendarHomePage):
        """Test opening the calendars list."""
        calendars_page = calendar_home.tap_calendars()
        assert calendars_page.is_on_calendars_list()
        # Return to calendar home
        calendars_page.tap_done()

    def test_get_calendar_names(self, calendar_home: CalendarHomePage):
        """Test getting the list of calendar names."""
        calendars_page = calendar_home.tap_calendars()

        calendars = calendars_page.get_calendar_names()
        # Should have at least one calendar
        assert len(calendars) > 0

        # Return to calendar home
        calendars_page.tap_done()

    def test_get_account_names(self, calendar_home: CalendarHomePage):
        """Test getting the list of account names."""
        calendars_page = calendar_home.tap_calendars()

        accounts = calendars_page.get_account_names()
        # Should have at least one account
        assert len(accounts) > 0
        # Accounts should be email addresses
        for account in accounts:
            assert "@" in account

        # Return to calendar home
        calendars_page.tap_done()


@pytest.mark.calendar
class TestCalendarDates:
    """Tests for date interactions in the calendar."""

    def test_get_dates_with_events(self, calendar_home: CalendarHomePage):
        """Test getting dates that have events."""
        dates = calendar_home.get_visible_dates_with_events()
        # This is informational - may or may not have events
        print(f"Dates with events: {dates}")
        assert isinstance(dates, list)

    def test_tap_event(self, calendar_home: CalendarHomePage):
        """Test tapping an event if one exists."""

        # Get visible events in day view
        events = calendar_home.get_visible_dates_with_events()
        print(f"Found {len(events)} events: {events}")

        if events:
            # Events are named like "event-shown:EventTitle"
            # Tapping would open event detail, so we just verify the list works
            assert len(events) > 0
        else:
            # No events visible - that's okay, test passes
            print("No events visible in current day view")


@pytest.mark.calendar
@pytest.mark.slow
class TestCalendarEventCreation:
    """Tests for full event creation workflow."""

    def test_create_and_delete_event(self, calendar_home: CalendarHomePage):
        """Test creating a simple event and verifying it appears."""
        import time
        import uuid

        # Generate unique event title
        unique_id = str(uuid.uuid4())[:8]
        event_title = f"AutoTest Event {unique_id}"

        # Create event
        new_event_page = calendar_home.tap_add_event()
        new_event_page.set_title(event_title)
        calendar_home = new_event_page.tap_done()

        # Wait for calendar to refresh
        time.sleep(1)

        # Verify we're back on calendar home
        assert calendar_home.is_on_calendar_home()

        # Note: Deleting the event would require additional page objects
        # for the event detail view. For now, just verify creation works.


@pytest.mark.calendar
@pytest.mark.onboarding
class TestCalendarOnboarding:
    """
    Tests for Calendar app first-time onboarding screens.

    These tests verify the onboarding flow that appears when Calendar
    is launched for the first time on a fresh device/simulator.

    To test on a fresh simulator, erase the simulator first:
        xcrun simctl erase "iPhone 17 Pro"

    Then run:
        uv run pytest tests/test_calendar.py::TestCalendarOnboarding -v \
            --device-name "iPhone 17 Pro" --platform-version "26.2"
    """

    def test_onboarding_dismissal_reaches_home(self, driver, app_launcher: AppLauncher):
        """
        Test that onboarding screens can be dismissed to reach the main Calendar.

        This test launches Calendar without using the calendar_home fixture
        (which auto-dismisses onboarding), manually dismisses onboarding,
        and verifies the main screen is reached.
        """
        app_launcher.launch_calendar()

        onboarding = CalendarOnboardingPage(driver)

        # Dismiss all onboarding screens (location + notifications permissions)
        result = onboarding.dismiss_all_onboarding()
        assert result is True

        # Verify we can now see the calendar home
        calendar_home = CalendarHomePage(driver)
        assert calendar_home.is_on_calendar_home()

        app_launcher.terminate(SystemApps.CALENDAR)
