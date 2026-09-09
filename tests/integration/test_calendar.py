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

from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.pages.calendar import CalendarHomePage, CalendarOnboardingPage
from uiautomation.utils.app_launcher import AppLauncher


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

    @pytest.mark.journey
    def test_navigate_to_month_view(self, calendar_home: CalendarHomePage):
        """Verify day-to-month navigation and an explicit return to day view."""
        if calendar_home.is_on_month_view(timeout=1):
            calendar_home.tap_today()
        calendar_home.wait_for_visible(calendar_home.DAY_VIEW_NAV_BAR)
        calendar_home.tap_back_to_month()
        assert calendar_home.is_on_month_view()
        calendar_home.tap_today()
        assert calendar_home.is_element_visible(calendar_home.DAY_VIEW_NAV_BAR)


@pytest.mark.calendar
class TestCalendarAddEvent:
    """Tests for creating calendar events."""

    @pytest.mark.journey
    def test_open_new_event(self, calendar_home: CalendarHomePage):
        """Test opening the new event screen."""
        new_event_page = calendar_home.tap_add_event()
        assert new_event_page.is_on_new_event_page()
        # Cancel to return to calendar; verify the sheet actually closes.
        home = new_event_page.tap_cancel()
        assert new_event_page.wait_for_invisible(new_event_page.TITLE_FIELD)
        assert home.is_on_calendar_home()

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

    @pytest.mark.real_device(reason="Simulator may not have any configured calendar accounts")
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
@pytest.mark.diagnostic
class TestCalendarDates:
    """Tests for date interactions in the calendar."""

    def test_get_dates_with_events(self, calendar_home: CalendarHomePage):
        """Test getting dates that have events."""
        dates = calendar_home.get_visible_dates_with_events()
        # This is informational - may or may not have events
        print(f"Dates with events: {dates}")
        assert isinstance(dates, list)


@pytest.mark.calendar
@pytest.mark.slow
class TestCalendarEventCreation:
    """Tests for full event creation workflow."""

    @pytest.mark.real_device(reason="Event draft dismissal returns inconsistent views on simulator")
    def test_create_event_draft_without_persisting(self, calendar_home: CalendarHomePage):
        """Test event creation flow without leaving persisted data behind."""
        import uuid

        # Generate unique event title
        unique_id = str(uuid.uuid4())[:8]
        event_title = f"AutoTest Event {unique_id}"

        new_event_page = calendar_home.tap_add_event()
        new_event_page.set_title(event_title)
        assert new_event_page.is_done_enabled()

        calendar_home = new_event_page.tap_cancel()
        assert calendar_home.is_on_calendar_home()


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
        uv run pytest --run-integration tests/integration/test_calendar.py::TestCalendarOnboarding -v \
            --device-name "iPhone 17 Pro" --platform-version "26.2"
    """

    def test_onboarding_dismissal_reaches_home(self, request, driver, app_launcher: AppLauncher):
        """
        Test that onboarding screens can be dismissed to reach the main Calendar.

        This test launches Calendar without using the calendar_home fixture
        (which auto-dismisses onboarding), manually dismisses onboarding,
        and verifies the main screen is reached.
        """
        request.addfinalizer(lambda: app_launcher.terminate(SystemApps.CALENDAR))
        app_launcher.terminate(SystemApps.CALENDAR)
        app_launcher.launch(SystemApps.CALENDAR)

        onboarding = CalendarOnboardingPage(driver)

        # Dismiss all onboarding screens (location + notifications permissions)
        result = onboarding.dismiss_all_onboarding()
        assert result is True

        # Verify we can now see the calendar home
        calendar_home = CalendarHomePage(driver)
        assert calendar_home.is_on_calendar_home()
