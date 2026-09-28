"""Settings switch actions confirm state on the outer control after a nested tap."""

from unittest.mock import MagicMock

import pytest
from selenium.webdriver.support.wait import WebDriverWait

from uiautomation.pages.settings.display_settings import DisplaySettingsPage
from uiautomation.pages.settings.settings_home import SettingsHomePage
from uiautomation.pages.settings.wifi_settings import WifiSettingsPage


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
