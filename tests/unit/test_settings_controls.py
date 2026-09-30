"""Settings switch actions confirm state on the outer control after a nested tap."""

from unittest.mock import MagicMock

import pytest
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support.wait import WebDriverWait

from uiautomation.pages.settings.display_settings import DisplaySettingsPage
from uiautomation.pages.settings.settings_home import SettingsHomePage
from uiautomation.pages.settings.wifi_settings import WifiSettingsPage


def test_display_navigation_propagates_broken_session() -> None:
    driver = MagicMock()
    driver.find_element.side_effect = WebDriverException("session lost")
    page = SettingsHomePage(driver)
    page.scroll_down = MagicMock()
    with pytest.raises(WebDriverException, match="session lost"):
        page.go_to_display_brightness()
    page.scroll_down.assert_not_called()


def test_display_navigation_scrolls_only_for_missing_element() -> None:
    driver = MagicMock()
    element = MagicMock()
    driver.find_element.side_effect = [NoSuchElementException(), element]
    page = SettingsHomePage(driver)
    page.scroll_down = MagicMock()
    assert isinstance(page.go_to_display_brightness(), DisplaySettingsPage)
    page.scroll_down.assert_called_once()
    element.click.assert_called_once()


def test_brightness_waits_for_reported_value_after_one_tap() -> None:
    driver = MagicMock()
    driver.find_element.return_value.rect = {"x": 0, "y": 0, "width": 100, "height": 10}
    page = DisplaySettingsPage(driver)
    page._wait = WebDriverWait(driver, 0.03, poll_frequency=0.001)
    page.get_brightness_level = MagicMock(side_effect=[0.1, StaleElementReferenceException(), 0.48])
    page.set_brightness_level(0.5)
    driver.execute_script.assert_called_once_with("mobile: tap", {"x": 50, "y": 5})


def test_brightness_unchanged_is_failure() -> None:
    driver = MagicMock()
    driver.find_element.return_value.rect = {"x": 0, "y": 0, "width": 100, "height": 10}
    page = DisplaySettingsPage(driver)
    page._wait = WebDriverWait(driver, 0)
    page.get_brightness_level = MagicMock(return_value=0.1)
    with pytest.raises(TimeoutException, match="Brightness did not reach"):
        page.set_brightness_level(0.5)


@pytest.mark.parametrize("level", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_brightness_target_never_mutates_device(level: float) -> None:
    driver = MagicMock()
    with pytest.raises(ValueError):
        DisplaySettingsPage(driver).set_brightness_level(level)
    driver.execute_script.assert_not_called()


@pytest.mark.parametrize(
    "value, expected", [("0%", 0.0), ("50%", 0.5), ("100%", 1.0), ("12.5%", 0.125), ("50", 0.5)]
)
def test_brightness_reads_reported_percentage(value: str, expected: float) -> None:
    driver = MagicMock()
    driver.find_element.return_value.get_attribute.return_value = value
    assert DisplaySettingsPage(driver).get_brightness_level() == expected


@pytest.mark.parametrize("value", [None, "", " ", "unknown", "50%%", "-1%", "101%", "NaN", "inf"])
def test_invalid_brightness_never_returns_a_plausible_default(value: str | None) -> None:
    driver = MagicMock()
    driver.find_element.return_value.get_attribute.return_value = value
    with pytest.raises(ValueError, match="Invalid brightness slider value"):
        DisplaySettingsPage(driver).get_brightness_level()


@pytest.mark.parametrize(
    "page_type, method, state_name",
    [
        (SettingsHomePage, "set_airplane_mode", "AIRPLANE_MODE"),
        (
            DisplaySettingsPage,
            "set_automatic_appearance",
            "AUTOMATIC_SWITCH",
        ),
        (DisplaySettingsPage, "set_true_tone", "TRUE_TONE_SWITCH"),
    ],
)
@pytest.mark.parametrize("inner_present", [True, False])
def test_nested_switch_uses_reported_state_and_available_tap_control(
    page_type: type[SettingsHomePage] | type[DisplaySettingsPage],
    method: str,
    state_name: str,
    inner_present: bool,
) -> None:
    driver, outer, inner = MagicMock(), MagicMock(), MagicMock()
    page = page_type(driver)
    page._wait = WebDriverWait(driver, 0.02, poll_frequency=0.001)
    state_locator = getattr(page, state_name)
    page.is_element_present = MagicMock(return_value=inner_present)
    driver.find_element.side_effect = lambda *locator: outer if locator == state_locator else inner
    outer.get_attribute.side_effect = ["0", "0", "1"]
    getattr(page, method)(True)
    (inner if inner_present else outer).click.assert_called_once()
    (outer if inner_present else inner).click.assert_not_called()
    assert outer.get_attribute.call_count == 3


@pytest.mark.parametrize(
    "method, before, after", [("enable_wifi", "0", "1"), ("disable_wifi", "1", "0")]
)
def test_wifi_state_changes_wait_for_the_final_value(method: str, before: str, after: str) -> None:
    driver, switch = MagicMock(), MagicMock()
    driver.find_element.return_value = switch
    switch.get_attribute.side_effect = [before, before, after]
    page = WifiSettingsPage(driver)
    page._wait = WebDriverWait(driver, 0.02, poll_frequency=0.001)
    getattr(page, method)()
    switch.click.assert_called_once()
    assert switch.get_attribute.call_count == 3
