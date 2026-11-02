"""Safari on pages served from this Mac (deterministic) and on apple.com (real world)."""

import pytest

from uiautomation.pages.safari import SafariPage

pytestmark = pytest.mark.safari

HOME_HEADING = SafariPage.text("UIAutomation fixture page")
SECOND_HEADING = SafariPage.text("Second fixture page")

# apple.com: only structure that outlives marketing copy (landmarks, menu, section links).
APPLE_URL = "https://www.apple.com"
APPLE_GLOBAL_NAV = SafariPage.web("Other", "Global, navigation")
APPLE_IPHONE_NAV = SafariPage.web("Other", "iPhone family, navigation")


@pytest.mark.smoke
def test_safari_is_ready(safari_home: SafariPage) -> None:
    """Safari reaches a usable address bar past its first-launch notices."""
    assert safari_home.is_element_visible(safari_home.TABS_BUTTON)


@pytest.mark.journey
def test_load_follow_link_and_go_back(safari_home: SafariPage, fixture_site: str) -> None:
    """A local page loads, a link navigates, and Back returns."""
    safari_home.open_url(fixture_site, HOME_HEADING)
    assert safari_home.host() == "127.0.0.1"
    safari_home.tap("Link", "Go to second page")
    safari_home.wait_for(SECOND_HEADING)
    safari_home.go_back(HOME_HEADING)


@pytest.mark.journey
def test_form_input_reaches_the_page(safari_home: SafariPage, fixture_site: str) -> None:
    """Typed text, including accents, reaches page script through a web input."""
    safari_home.open_url(fixture_site, HOME_HEADING)
    safari_home.fill("Fixture input", "héllo 42")
    safari_home.tap("Button", "Echo")
    safari_home.wait_for_text("Echo: héllo 42")


@pytest.mark.network
@pytest.mark.journey
def test_apple_com_menu_to_iphone_and_back(safari_home: SafariPage) -> None:
    """apple.com loads over HTTPS; the site menu reaches the iPhone section; Back returns.

    When apple.com's structure changes, update the locators above.
    """
    safari_home.open_url(APPLE_URL, APPLE_GLOBAL_NAV)
    assert safari_home.host() == "apple.com"
    safari_home.tap("Button", "Menu")
    safari_home.tap("Button", "iPhone menu")
    safari_home.tap("Link", "Explore All iPhone")
    safari_home.wait_for(APPLE_IPHONE_NAV)
    assert safari_home.host() == "apple.com"
    safari_home.go_back(APPLE_GLOBAL_NAV)
    safari_home.wait_for_invisible(APPLE_IPHONE_NAV)
    assert safari_home.is_showing(safari_home.FORWARD_BUTTON)
