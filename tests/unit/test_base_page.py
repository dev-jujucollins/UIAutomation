"""Tests for base page."""

from unittest.mock import MagicMock

import pytest
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support.wait import WebDriverWait

from uiautomation.pages.base_page import BasePage


@pytest.mark.parametrize(
    "value, expected", [("false", "false"), ("", ""), (None, None), ({"value": 1}, None)]
)
def test_text_attribute_contract(value: str | dict[str, int] | None, expected: str | None) -> None:
    page = BasePage(MagicMock())
    page.find_element = MagicMock(
        return_value=MagicMock(get_attribute=MagicMock(return_value=value))
    )
    assert page.get_attribute(("accessibility id", "label"), "label") == expected


def test_invisibility_returns_boolean_when_selenium_returns_an_element() -> None:
    page = BasePage(MagicMock())
    page._get_wait = MagicMock(return_value=MagicMock(until=MagicMock(return_value=MagicMock())))
    assert page.wait_for_invisible(("accessibility id", "label")) is True


def quick_page(driver: MagicMock) -> BasePage:
    page = BasePage(driver)
    page._wait = WebDriverWait(driver, 0.02, poll_frequency=0.001)
    return page


def test_switch_waits_for_delayed_state_without_toggling_twice() -> None:
    driver, switch = MagicMock(), MagicMock()
    driver.find_element.return_value = switch
    switch.get_attribute.side_effect = ["0", "0", StaleElementReferenceException(), "1"]
    quick_page(driver).set_switch_state(("accessibility id", "switch"), True)
    switch.click.assert_called_once()
    assert driver.find_element.call_count == 4


def test_switch_does_not_toggle_again_after_stale_click_response() -> None:
    driver, switch = MagicMock(), MagicMock()
    driver.find_element.return_value = switch
    switch.get_attribute.side_effect = ["0", "0", "1"]
    switch.click.side_effect = StaleElementReferenceException()
    quick_page(driver).set_switch_state(("accessibility id", "switch"), True)
    switch.click.assert_called_once()


def test_switch_retries_a_stale_read_before_click() -> None:
    driver, switch = MagicMock(), MagicMock()
    driver.find_element.return_value = switch
    switch.get_attribute.side_effect = [StaleElementReferenceException(), "1", "0"]
    quick_page(driver).set_switch_state(("accessibility id", "switch"), False)
    switch.click.assert_called_once()


def test_switch_already_in_requested_state_is_not_clicked() -> None:
    driver, switch = MagicMock(), MagicMock()
    driver.find_element.return_value = switch
    switch.get_attribute.return_value = "1"
    quick_page(driver).set_switch_state(("accessibility id", "switch"), True)
    switch.click.assert_not_called()


@pytest.mark.parametrize("initial, expected_clicks", [("0", 1), (None, 0)])
def test_switch_requires_confirmed_state(initial: str | None, expected_clicks: int) -> None:
    driver, switch = MagicMock(), MagicMock()
    driver.find_element.return_value = switch
    switch.get_attribute.return_value = initial
    with pytest.raises(TimeoutException, match="did not reach value"):
        quick_page(driver).set_switch_state(("accessibility id", "switch"), True)
    assert switch.click.call_count == expected_clicks


def test_switch_does_not_swallow_connection_errors() -> None:
    driver = MagicMock()
    driver.find_element.side_effect = WebDriverException("disconnected")
    with pytest.raises(WebDriverException, match="disconnected"):
        quick_page(driver).set_switch_state(("accessibility id", "switch"), True)


def test_attribute_wait_refinds_a_stale_control_until_value_matches() -> None:
    driver, field = MagicMock(), MagicMock()
    driver.find_element.return_value = field
    field.get_attribute.side_effect = [StaleElementReferenceException(), "old", "new"]
    quick_page(driver).wait_for_attribute(("accessibility id", "field"), "value", "new")
    assert driver.find_element.call_count == 3


@pytest.mark.parametrize("max_scrolls", [0, 1, 3])
def test_scroll_checks_the_target_after_the_last_allowed_scroll(max_scrolls: int) -> None:
    page = BasePage(MagicMock())
    page.is_element_visible = MagicMock(side_effect=[False] * max_scrolls + [True])
    page.scroll_down = MagicMock()
    element = MagicMock()
    page.find_element = MagicMock(return_value=element)
    assert (
        page.scroll_to_element(("accessibility id", "target"), max_scrolls=max_scrolls) is element
    )
    assert page.scroll_down.call_count == max_scrolls


def test_scroll_stops_at_the_allowed_count_when_target_is_missing() -> None:
    page = BasePage(MagicMock())
    page.is_element_visible = MagicMock(return_value=False)
    page.scroll_up = MagicMock()
    assert page.scroll_to_element(("accessibility id", "target"), 2, "up") is None
    assert page.scroll_up.call_count == 2


@pytest.mark.parametrize("max_scrolls, direction", [(-1, "down"), (1, "sideways")])
def test_scroll_rejects_invalid_limits_and_directions(max_scrolls: int, direction: str) -> None:
    with pytest.raises(ValueError):
        BasePage(MagicMock()).scroll_to_element(
            ("accessibility id", "target"), max_scrolls, direction
        )
