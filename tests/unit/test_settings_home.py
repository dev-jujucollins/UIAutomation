"""Tests for settings home."""

from unittest.mock import MagicMock

import pytest

from uiautomation.pages.settings.settings_home import SettingsHomePage


def settings_xml(rows: str, extra: str = "", app_name: str = "Settings") -> str:
    """Build a small realistic hierarchy instead of mocking each locator."""
    return f'''<AppiumAUT><XCUIElementTypeApplication name="{app_name}" visible="true">
    <XCUIElementTypeCollectionView visible="true">{rows}</XCUIElementTypeCollectionView>
    {extra}</XCUIElementTypeApplication></AppiumAUT>'''


def row(name: str, visible: str = "true") -> str:
    """Create a home-row element."""
    return f'<XCUIElementTypeButton name="com.apple.settings.{name}" visible="{visible}"/>'


@pytest.mark.parametrize("names", [("wifi", "bluetooth"), ("general", "accessibility")])
def test_readiness_accepts_device_and_simulator_anchors(names: tuple[str, str]) -> None:
    driver = MagicMock()
    driver.page_source = settings_xml("".join(row(name) for name in names))
    page = SettingsHomePage(driver)
    assert page.is_home_visually_ready()
    driver.find_element.assert_not_called()


@pytest.mark.parametrize(
    "source, message",
    [
        ("", "invalid XML"),
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
    driver = MagicMock(page_source=source)
    assert message in SettingsHomePage(driver).get_home_readiness_failures()[0]


def test_readiness_ignores_hidden_error_words() -> None:
    driver = MagicMock(
        page_source=settings_xml(
            row("general") + row("accessibility"),
            '<XCUIElementTypeStaticText visible="false" label="SpringBoard Cannot Connect"/>',
        )
    )
    assert SettingsHomePage(driver).is_home_visually_ready()


def test_readiness_waits_for_snapshot_to_become_ready() -> None:
    page = SettingsHomePage(MagicMock())
    page.get_page_source = MagicMock(
        side_effect=["", settings_xml(row("general") + row("accessibility"))]
    )
    page.assert_home_visually_ready()
    assert page.get_page_source.call_count == 2


def test_readiness_timeout_reports_latest_failure() -> None:
    page = SettingsHomePage(MagicMock(page_source=settings_xml(row("wifi"))))
    page.DEFAULT_TIMEOUT = 0
    with pytest.raises(AssertionError, match="fewer than two"):
        page.assert_home_visually_ready()
