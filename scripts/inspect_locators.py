"""
Developer tool: capture XML page source from various app screens to discover locators.

Not part of the test suite (pyproject.toml sets testpaths=["tests"], so `pytest`
alone will not collect this file). Run explicitly:

    uv run pytest scripts/inspect_locators.py -v
    uv run pytest scripts/inspect_locators.py -v -k wifi
    uv run pytest scripts/inspect_locators.py -v -k calendar

Output XML files are written to debug_output/ at the project root.
"""

import time
from pathlib import Path

import pytest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.action_chains import ActionChains

from src.pages.settings import SettingsHomePage

OUTPUT_DIR = Path(__file__).parent.parent / "debug_output"


@pytest.fixture(scope="module", autouse=True)
def setup_output_dir():
    OUTPUT_DIR.mkdir(exist_ok=True)
    yield


def save_page_source(driver, filename: str) -> str:
    filepath = OUTPUT_DIR / filename
    filepath.write_text(driver.page_source)
    print(f"\nSaved page source to: {filepath}")
    return str(filepath)


class TestSettingsHome:
    """Capture Settings home page source."""

    def test_settings_home_top(self, settings_app: SettingsHomePage):
        for _ in range(3):
            settings_app.scroll_up()
        time.sleep(0.5)
        save_page_source(settings_app.driver, "01_settings_home_top.xml")

    def test_settings_home_middle(self, settings_app: SettingsHomePage):
        settings_app.scroll_down()
        settings_app.scroll_down()
        time.sleep(0.5)
        save_page_source(settings_app.driver, "02_settings_home_middle.xml")

    def test_settings_home_bottom(self, settings_app: SettingsHomePage):
        for _ in range(5):
            settings_app.scroll_down()
        time.sleep(0.5)
        save_page_source(settings_app.driver, "03_settings_home_bottom.xml")


class TestWifiPage:
    """Capture Wi-Fi settings page source."""

    def test_wifi_top(self, settings_app: SettingsHomePage):
        wifi_page = settings_app.go_to_wifi()
        time.sleep(2)
        save_page_source(wifi_page.driver, "04_wifi_top.xml")

    def test_wifi_networks(self, settings_app: SettingsHomePage):
        wifi_page = settings_app.go_to_wifi()
        time.sleep(3)
        wifi_page.scroll_down()
        save_page_source(wifi_page.driver, "05_wifi_networks.xml")


class TestDisplayPage:
    """Capture Display & Brightness page source."""

    def test_display_top(self, settings_app: SettingsHomePage):
        display_page = settings_app.go_to_display_brightness()
        time.sleep(1)
        save_page_source(display_page.driver, "06_display_top.xml")

    def test_display_middle(self, settings_app: SettingsHomePage):
        display_page = settings_app.go_to_display_brightness()
        display_page.scroll_down()
        time.sleep(0.5)
        save_page_source(display_page.driver, "07_display_middle.xml")

    def test_display_bottom(self, settings_app: SettingsHomePage):
        display_page = settings_app.go_to_display_brightness()
        display_page.scroll_down()
        display_page.scroll_down()
        time.sleep(0.5)
        save_page_source(display_page.driver, "08_display_bottom.xml")


class TestGeneralPage:
    """Capture General settings page source."""

    def test_general_top(self, settings_app: SettingsHomePage):
        general_page = settings_app.go_to_general()
        time.sleep(1)
        save_page_source(general_page.driver, "09_general_top.xml")

    def test_general_middle(self, settings_app: SettingsHomePage):
        general_page = settings_app.go_to_general()
        general_page.scroll_down()
        general_page.scroll_down()
        time.sleep(0.5)
        save_page_source(general_page.driver, "10_general_middle.xml")

    def test_general_bottom(self, settings_app: SettingsHomePage):
        general_page = settings_app.go_to_general()
        for _ in range(5):
            general_page.scroll_down()
        time.sleep(0.5)
        save_page_source(general_page.driver, "11_general_bottom.xml")


class TestAboutPage:
    """Capture About page source."""

    def test_about_top(self, settings_app: SettingsHomePage):
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()
        time.sleep(1)
        save_page_source(about_page.driver, "12_about_top.xml")

    def test_about_bottom(self, settings_app: SettingsHomePage):
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()
        about_page.scroll_down()
        about_page.scroll_down()
        time.sleep(0.5)
        save_page_source(about_page.driver, "13_about_bottom.xml")


class TestCalendarApp:
    """Capture Calendar app page source."""

    def test_calendar_home(self, calendar_app):
        time.sleep(2)
        save_page_source(calendar_app, "14_calendar_home.xml")

    def test_calendar_day_view(self, calendar_app):
        time.sleep(1)
        try:
            calendar_app.find_element(
                AppiumBy.IOS_PREDICATE, "label == 'Day' OR name == 'Day'"
            ).click()
            time.sleep(1)
        except Exception:
            pass
        save_page_source(calendar_app, "15_calendar_day_view.xml")

    def test_calendar_add_event(self, calendar_app):
        time.sleep(1)
        try:
            calendar_app.find_element(
                AppiumBy.IOS_PREDICATE, "label == 'Add' OR name == 'Add'"
            ).click()
            time.sleep(1)
        except Exception:
            pass
        save_page_source(calendar_app, "16_calendar_add_event.xml")

    def test_calendar_add_event_scrolled(self, calendar_app):
        time.sleep(1)
        try:
            calendar_app.find_element(
                AppiumBy.IOS_PREDICATE, "label == 'Add' OR name == 'Add'"
            ).click()
            time.sleep(1)

            try:
                calendar_app.find_element(
                    AppiumBy.IOS_PREDICATE, "label CONTAINS 'Starts' OR name CONTAINS 'Starts'"
                ).click()
                time.sleep(0.5)
            except Exception:
                pass

            size = calendar_app.get_window_size()
            start_y = int(size["height"] * 0.5)
            end_y = int(size["height"] * 0.25)
            center_x = int(size["width"] * 0.5)

            actions = ActionChains(calendar_app)
            actions.w3c_actions.pointer_action.move_to_location(center_x, start_y)
            actions.w3c_actions.pointer_action.pointer_down()
            actions.w3c_actions.pointer_action.move_to_location(center_x, end_y)
            actions.w3c_actions.pointer_action.pointer_up()
            actions.perform()
            time.sleep(0.5)
        except Exception as e:
            print(f"Error during scroll: {e}")
        save_page_source(calendar_app, "17_calendar_add_event_scrolled.xml")

    def test_calendar_calendars_list(self, calendar_app):
        time.sleep(1)
        try:
            calendar_app.find_element(
                AppiumBy.IOS_PREDICATE, "label == 'Calendars' OR name == 'Calendars'"
            ).click()
            time.sleep(1)
        except Exception:
            pass
        save_page_source(calendar_app, "18_calendar_calendars_list.xml")
