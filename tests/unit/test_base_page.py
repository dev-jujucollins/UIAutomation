"""Tests for base page."""

from unittest.mock import MagicMock

import pytest

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
