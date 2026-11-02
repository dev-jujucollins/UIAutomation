"""The Reminders overview swipes its own list to reach My Lists at large text sizes."""

from unittest.mock import MagicMock

import pytest

from uiautomation.pages.reminders import RemindersHomePage


def _page(appear_after_swipes: int) -> tuple[RemindersHomePage, MagicMock]:
    driver = MagicMock()
    cell = MagicMock()
    cell.get_attribute.return_value = "Reminders, 2 reminders"
    swipes = {"count": 0}

    def find_elements(by: str, value: str) -> list[MagicMock]:
        if "Reminders, " in value:
            return [cell] if swipes["count"] >= appear_after_swipes else []
        return []

    def execute_script(script: str, args: dict) -> None:
        assert script == "mobile: swipe" and args["direction"] == "up"
        swipes["count"] += 1

    driver.find_elements.side_effect = find_elements
    driver.execute_script.side_effect = execute_script
    page = RemindersHomePage(driver)
    page.find_element = MagicMock(return_value=MagicMock(id="table"))
    return page, driver


@pytest.mark.parametrize("swipes", [0, 3])
def test_list_count_swipes_until_the_list_appears(swipes: int) -> None:
    page, driver = _page(swipes)
    assert page.list_count() == 2
    assert driver.execute_script.call_count == swipes


def test_missing_list_fails_after_bounded_swipes() -> None:
    page, driver = _page(99)
    with pytest.raises(AssertionError, match="not found after 5 swipes"):
        page.list_count()
    assert driver.execute_script.call_count == 5
