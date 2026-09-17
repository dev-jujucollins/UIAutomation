"""Tests for settings home."""

from unittest.mock import MagicMock, PropertyMock
from xml.etree import ElementTree

import pytest
from selenium.common.exceptions import StaleElementReferenceException

from uiautomation.pages.settings.settings_home import SettingsHomePage


def settings_xml(rows: str, extra: str = "", app_name: str = "Settings") -> str:
    """Build a small realistic hierarchy instead of mocking each locator."""
    return f'''<AppiumAUT><XCUIElementTypeApplication name="{app_name}" visible="true">
    <XCUIElementTypeCollectionView visible="true">{rows}</XCUIElementTypeCollectionView>
    {extra}</XCUIElementTypeApplication></AppiumAUT>'''


def row(name: str, visible: str = "true") -> str:
    """Create a home-row element."""
    return f'<XCUIElementTypeButton name="com.apple.settings.{name}" visible="{visible}"/>'


def driver_from_xml(source: str) -> MagicMock:
    """Model live element queries from a small accessibility fixture."""
    driver = MagicMock()
    type(driver).page_source = PropertyMock(side_effect=AssertionError("Must not fetch XML"))
    try:
        root = ElementTree.fromstring(source)
    except ElementTree.ParseError:
        driver.find_elements.return_value = []
        return driver

    def element(node: ElementTree.Element) -> MagicMock:
        result = MagicMock()
        result.is_displayed.return_value = node.get("visible") == "true"
        result.get_attribute.side_effect = node.get

        def find(by: str, value: str) -> list[MagicMock]:
            descendants = list(node.iter())[1:]
            if by == SettingsHomePage.By.CLASS_NAME:
                return [element(child) for child in descendants if child.tag == value]
            return [
                element(child)
                for child in descendants
                if child.get("name") in SettingsHomePage.INITIAL_SCREEN_ANCHOR_NAMES
            ]

        result.find_elements.side_effect = find
        return result

    driver.find_elements.return_value = [
        element(node)
        for node in root.iter("XCUIElementTypeApplication")
        if node.get("name") == "Settings"
    ]
    return driver


@pytest.mark.parametrize("names", [("wifi", "bluetooth"), ("general", "accessibility")])
def test_readiness_accepts_device_and_simulator_anchors(names: tuple[str, str]) -> None:
    driver = driver_from_xml(settings_xml("".join(row(name) for name in names)))
    page = SettingsHomePage(driver)
    assert page.is_home_visually_ready()
    driver.find_element.assert_not_called()


@pytest.mark.parametrize(
    "source, message",
    [
        ("", "root"),
        (settings_xml(row("wifi") + row("bluetooth"), app_name="SpringBoard"), "root"),
        (settings_xml(row("wifi") + row("wifi")), "two expected"),
        (settings_xml(row("wifi") + row("bluetooth", "false")), "two expected"),
        (
            settings_xml(row("wifi") + row("bluetooth"), '<XCUIElementTypeAlert visible="true"/>'),
            "alert",
        ),
        ('<XCUIElementTypeApplication name="Settings" visible="true"/>', "list"),
    ],
    ids=["empty", "springboard", "duplicate-row", "hidden-row", "alert", "missing-list"],
)
def test_readiness_rejects_unusable_home(source: str, message: str) -> None:
    driver = driver_from_xml(source)
    assert message in SettingsHomePage(driver).get_home_readiness_failures()[0]


def test_readiness_ignores_hidden_error_words() -> None:
    driver = driver_from_xml(
        settings_xml(
            row("general") + row("accessibility"),
            '<XCUIElementTypeStaticText visible="false" label="SpringBoard Cannot Connect"/>',
        )
    )
    assert SettingsHomePage(driver).is_home_visually_ready()


def test_readiness_waits_for_elements_to_become_ready() -> None:
    page = SettingsHomePage(MagicMock())
    page.get_home_readiness_failures = MagicMock(side_effect=[["not ready"], []])
    page.assert_home_visually_ready()
    assert page.get_home_readiness_failures.call_count == 2


def test_readiness_timeout_reports_latest_failure() -> None:
    page = SettingsHomePage(driver_from_xml(settings_xml(row("wifi"))))
    page.DEFAULT_TIMEOUT = 0
    with pytest.raises(AssertionError, match="fewer than two"):
        page.assert_home_visually_ready()


def test_readiness_retries_a_stale_hierarchy() -> None:
    driver = MagicMock()
    driver.find_elements.side_effect = StaleElementReferenceException()
    assert SettingsHomePage(driver).get_home_readiness_failures() == [
        "Settings hierarchy changed during readiness check"
    ]
