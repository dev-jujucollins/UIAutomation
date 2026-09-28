"""Selected-date assertions reject wrong dates and incomplete labels."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from uiautomation.pages.calendar import CalendarHomePage


@pytest.mark.parametrize(
    "label, expected",
    [
        ("Sunday – Sep 27, 2026", date(2026, 9, 27)),
        ("Monday, January 12, 2026", date(2026, 1, 12)),
        ("February 29, 2028", date(2028, 2, 29)),
    ],
)
def test_selected_date_parses_english_day_labels(label: str, expected: date) -> None:
    assert CalendarHomePage.parse_selected_date(label) == expected


@pytest.mark.parametrize("label", ["Today", "September", "February 29, 2026", ""])
def test_selected_date_rejects_incomplete_or_invalid_dates(label: str) -> None:
    with pytest.raises(ValueError):
        CalendarHomePage.parse_selected_date(label)


def test_visible_today_control_does_not_imply_today_is_selected() -> None:
    page = CalendarHomePage(MagicMock())
    page.driver.execute_script.return_value = "2026-09-27"
    page.get_attribute = MagicMock(return_value="Monday – Sep 28, 2026")
    assert not page.is_today_selected()
    page.get_attribute.return_value = "Sunday – Sep 27, 2026"
    assert page.is_today_selected()


def test_missing_date_label_fails_instead_of_claiming_today() -> None:
    page = CalendarHomePage(MagicMock())
    page.get_attribute = MagicMock(return_value=None)
    with pytest.raises(ValueError, match="no date label"):
        page.get_selected_date()
