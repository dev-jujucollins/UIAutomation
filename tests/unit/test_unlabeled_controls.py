"""Unlabeled-control reporting uses one device-side query and names each offender."""

from unittest.mock import MagicMock

from selenium.common.exceptions import StaleElementReferenceException

from uiautomation.pages.base_page import BasePage
from uiautomation.utils.local_runner import SUITES


def _element(kind: str, name: str | None, x: int = 10, y: int = 20) -> MagicMock:
    element = MagicMock()
    element.get_attribute.side_effect = {"type": f"XCUIElementType{kind}", "name": name}.get
    element.rect = {"x": x, "y": y, "width": 44, "height": 44}
    return element


def test_query_targets_visible_unlabeled_controls_only() -> None:
    driver = MagicMock()
    driver.find_elements.return_value = []
    assert BasePage(driver).unlabeled_controls() == []
    by, query = driver.find_elements.call_args.args
    assert by == BasePage.By.IOS_PREDICATE
    assert "visible == 1" in query and "accessible == 1" in query
    assert "(label == nil OR label == '')" in query
    for kind in ("Button", "Switch", "TextField", "Link"):
        assert f"'XCUIElementType{kind}'" in query
    assert "Cell" not in query  # layout containers legitimately have no label


def test_each_offender_is_described_and_stale_ones_skipped() -> None:
    stale = MagicMock()
    stale.get_attribute.side_effect = StaleElementReferenceException()
    driver = MagicMock()
    driver.find_elements.return_value = [
        _element("Button", "close"),
        stale,
        _element("Switch", None),
    ]
    assert BasePage(driver).unlabeled_controls() == [
        "Button name='close' at (10, 20)",
        "Switch name=None at (10, 20)",
    ]


def test_accessibility_suite_runs_only_opt_in_diagnostics() -> None:
    assert SUITES["accessibility"] == [
        "tests/integration",
        "--run-integration",
        "--run-diagnostics",
        "-m",
        "accessibility",
    ]
