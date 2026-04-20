"""Capture XML page source from app screens for locator discovery.

This helper lives outside `tests/` so it is not part of the default test suite.
Run it explicitly:

    uv run pytest scripts/inspect_locators.py -v
    uv run pytest scripts/inspect_locators.py -v -k wifi
    uv run pytest scripts/inspect_locators.py -v -k calendar

Output XML files are written to `debug_output/` at the project root.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.action_chains import ActionChains

from src.drivers.ios_driver import SystemApps
from src.pages.calendar import CalendarOnboardingPage
from src.pages.settings import SettingsHomePage
from src.utils.app_launcher import AppLauncher

if TYPE_CHECKING:
    from appium.webdriver.webdriver import WebDriver


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "debug_output"


@pytest.fixture(scope="module", autouse=True)
def setup_output_dir() -> None:
    """Create output directory for page source files."""
    OUTPUT_DIR.mkdir(exist_ok=True)


def save_page_source(driver: object, filename: str) -> str:
    """Save page source to file and return the path."""
    filepath = OUTPUT_DIR / filename
    page_source = cast(Any, driver).page_source
    filepath.write_text(str(page_source), encoding="utf-8")
    print(f"\nSaved page source to: {filepath}")
    return str(filepath)


@pytest.fixture(scope="function")
def calendar_app(driver: WebDriver, app_launcher: AppLauncher):
    """Launch Calendar and provide driver for debug capture."""
    app_launcher.launch(SystemApps.CALENDAR)
    onboarding = CalendarOnboardingPage(driver)
    assert onboarding.dismiss_all_onboarding(), "Failed to dismiss Calendar onboarding"

    yield driver

    app_launcher.terminate(SystemApps.CALENDAR)


class TestSettingsHome:
    """Capture Settings home page source."""

    def test_settings_home_top(self, settings_app: SettingsHomePage) -> None:
        """Capture Settings home top of page with search field."""
        for _ in range(3):
            settings_app.scroll_up()
        time.sleep(0.5)

        save_page_source(settings_app.driver, "01_settings_home_top.xml")
        print("\nLook for: Search field, Apple ID, Airplane Mode, Wi-Fi, Bluetooth")

    def test_settings_home_middle(self, settings_app: SettingsHomePage) -> None:
        """Capture Settings home middle section."""
        settings_app.scroll_down()
        settings_app.scroll_down()
        time.sleep(0.5)

        save_page_source(settings_app.driver, "02_settings_home_middle.xml")
        print("\nLook for: General, Display & Brightness, Accessibility")

    def test_settings_home_bottom(self, settings_app: SettingsHomePage) -> None:
        """Capture Settings home bottom section."""
        for _ in range(5):
            settings_app.scroll_down()
        time.sleep(0.5)

        save_page_source(settings_app.driver, "03_settings_home_bottom.xml")
        print("\nLook for: Battery, Privacy, App Store, etc.")


class TestWifiPage:
    """Capture Wi-Fi settings page source."""

    def test_wifi_top(self, settings_app: SettingsHomePage) -> None:
        """Capture Wi-Fi page top with switch."""
        wifi_page = settings_app.go_to_wifi()
        time.sleep(2)

        save_page_source(wifi_page.driver, "04_wifi_top.xml")
        print("\nLook for: Wi-Fi switch, Back button")

    def test_wifi_networks(self, settings_app: SettingsHomePage) -> None:
        """Capture Wi-Fi page networks list."""
        wifi_page = settings_app.go_to_wifi()
        time.sleep(3)
        wifi_page.scroll_down()

        save_page_source(wifi_page.driver, "05_wifi_networks.xml")
        print("\nLook for: Networks section, My Networks, available network cells")


class TestDisplayPage:
    """Capture Display & Brightness page source."""

    def test_display_top(self, settings_app: SettingsHomePage) -> None:
        """Capture Display page top with appearance options."""
        display_page = settings_app.go_to_display_brightness()
        time.sleep(1)

        save_page_source(display_page.driver, "06_display_top.xml")
        print("\nLook for: Light/Dark buttons, Automatic switch, Brightness slider")

    def test_display_middle(self, settings_app: SettingsHomePage) -> None:
        """Capture Display page middle section."""
        display_page = settings_app.go_to_display_brightness()
        display_page.scroll_down()
        time.sleep(0.5)

        save_page_source(display_page.driver, "07_display_middle.xml")
        print("\nLook for: True Tone, Night Shift, Auto-Lock")

    def test_display_bottom(self, settings_app: SettingsHomePage) -> None:
        """Capture Display page bottom section."""
        display_page = settings_app.go_to_display_brightness()
        display_page.scroll_down()
        display_page.scroll_down()
        time.sleep(0.5)

        save_page_source(display_page.driver, "08_display_bottom.xml")
        print("\nLook for: Text Size, Bold Text, Display Zoom")


class TestGeneralPage:
    """Capture General settings page source."""

    def test_general_top(self, settings_app: SettingsHomePage) -> None:
        """Capture General page top section."""
        general_page = settings_app.go_to_general()
        time.sleep(1)

        save_page_source(general_page.driver, "09_general_top.xml")
        print("\nLook for: About, Software Update, AirDrop")

    def test_general_middle(self, settings_app: SettingsHomePage) -> None:
        """Capture General page middle section."""
        general_page = settings_app.go_to_general()
        general_page.scroll_down()
        general_page.scroll_down()
        time.sleep(0.5)

        save_page_source(general_page.driver, "10_general_middle.xml")
        print("\nLook for: iPhone Storage, Background App Refresh, Date & Time")

    def test_general_bottom(self, settings_app: SettingsHomePage) -> None:
        """Capture General page bottom section."""
        general_page = settings_app.go_to_general()
        for _ in range(5):
            general_page.scroll_down()
        time.sleep(0.5)

        save_page_source(general_page.driver, "11_general_bottom.xml")
        print("\nLook for: VPN, Transfer or Reset, Shut Down")


class TestAboutPage:
    """Capture About page source."""

    def test_about_top(self, settings_app: SettingsHomePage) -> None:
        """Capture About page top section."""
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()
        time.sleep(1)

        save_page_source(about_page.driver, "12_about_top.xml")
        print("\nLook for: Name, iOS Version, Model Name")

    def test_about_bottom(self, settings_app: SettingsHomePage) -> None:
        """Capture About page bottom section with storage info."""
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()
        about_page.scroll_down()
        about_page.scroll_down()
        time.sleep(0.5)

        save_page_source(about_page.driver, "13_about_bottom.xml")
        print("\nLook for: Serial Number, Wi-Fi Address, Capacity, Available")


class TestCalendarApp:
    """Capture Calendar app page source."""

    def test_calendar_home(self, calendar_app: WebDriver) -> None:
        """Capture Calendar home page month view."""
        time.sleep(2)

        save_page_source(calendar_app, "14_calendar_home.xml")
        print("\nLook for: Today button, Add event button, Month/Week/Day view controls")

    def test_calendar_day_view(self, calendar_app: WebDriver) -> None:
        """Capture Calendar day view."""
        time.sleep(1)

        try:
            day_button = calendar_app.find_element(
                AppiumBy.IOS_PREDICATE, "label == 'Day' OR name == 'Day'"
            )
            day_button.click()
            time.sleep(1)
        except Exception:
            pass

        save_page_source(calendar_app, "15_calendar_day_view.xml")
        print("\nLook for: Day view elements, time slots, events")

    def test_calendar_add_event(self, calendar_app: WebDriver) -> None:
        """Capture Add Event screen."""
        time.sleep(1)

        try:
            add_button = calendar_app.find_element(
                AppiumBy.IOS_PREDICATE, "label == 'Add' OR name == 'Add'"
            )
            add_button.click()
            time.sleep(1)
        except Exception:
            pass

        save_page_source(calendar_app, "16_calendar_add_event.xml")
        print("\nLook for: Title field, Start/End date pickers, Location, Notes")

    def test_calendar_add_event_scrolled(self, calendar_app: WebDriver) -> None:
        """Capture Add Event screen after scrolling."""
        time.sleep(1)

        try:
            add_button = calendar_app.find_element(
                AppiumBy.IOS_PREDICATE, "label == 'Add' OR name == 'Add'"
            )
            add_button.click()
            time.sleep(1)

            try:
                starts_element = calendar_app.find_element(
                    AppiumBy.IOS_PREDICATE, "label CONTAINS 'Starts' OR name CONTAINS 'Starts'"
                )
                starts_element.click()
                time.sleep(0.5)
            except Exception:
                pass

            screen_size = calendar_app.get_window_size()
            start_y = int(screen_size["height"] * 0.5)
            end_y = int(screen_size["height"] * 0.25)
            center_x = int(screen_size["width"] * 0.5)

            actions = ActionChains(calendar_app)
            actions.w3c_actions.pointer_action.move_to_location(center_x, start_y)
            actions.w3c_actions.pointer_action.pointer_down()
            actions.w3c_actions.pointer_action.move_to_location(center_x, end_y)
            actions.w3c_actions.pointer_action.pointer_up()
            actions.perform()
            time.sleep(0.5)
        except Exception as error:
            print(f"Error during scroll: {error}")

        save_page_source(calendar_app, "17_calendar_add_event_scrolled.xml")
        print("\nLook for: Calendar picker, URL, Attachments, Alert options")

    def test_calendar_calendars_list(self, calendar_app: WebDriver) -> None:
        """Capture Calendars list view."""
        time.sleep(1)

        try:
            calendars_button = calendar_app.find_element(
                AppiumBy.IOS_PREDICATE, "label == 'Calendars' OR name == 'Calendars'"
            )
            calendars_button.click()
            time.sleep(1)
        except Exception:
            pass

        save_page_source(calendar_app, "18_calendar_calendars_list.xml")
        print("\nLook for: Calendar names, checkboxes, Add Calendar button")
