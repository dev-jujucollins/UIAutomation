"""Regression cases for literal text inside iOS predicates."""

import pytest

from uiautomation.utils.locators import predicate_literal


@pytest.mark.parametrize(
    "value, expected",
    [
        ("", "''"),
        ("Work", "'Work'"),
        ("Julius's Calendar", "'Julius\\'s Calendar'"),
        ("C:\\Calendar", "'C:\\\\Calendar'"),
        ('Family "Calendar"', "'Family \"Calendar\"'"),
        ("日历", "'日历'"),
    ],
)
def test_predicate_values_are_quoted_as_literals(value: str, expected: str) -> None:
    assert predicate_literal(value) == expected
