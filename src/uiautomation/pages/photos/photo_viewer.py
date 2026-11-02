"""One-up photo viewer opened from the Photos library grid."""

from __future__ import annotations

from typing import TYPE_CHECKING

from uiautomation.utils.locators import predicate_literal

from ..base_page import BasePage

if TYPE_CHECKING:
    from .photos_library import PhotosLibraryPage


class PhotoViewerPage(BasePage):
    """Shows one photo with its date ("October 9, 2009", or "Today") and actions."""

    NAVIGATION_BAR = (BasePage.By.ACCESSIBILITY_ID, "PUOneUpView")
    BACK_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "BackButton")
    FAVORITE = (BasePage.By.ACCESSIBILITY_ID, "PUOneUpBarButtonItemIdentifierFavorite")
    DELETE_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "PUOneUpBarButtonItemIdentifierTrashBin")
    # "This photo will be deleted from the library. It will be in Recently Deleted for 30 days."
    DELETE_CONFIRM = (BasePage.By.ACCESSIBILITY_ID, "Delete Photo")

    HEALTH_LOCATORS = ("NAVIGATION_BAR", "BACK_BUTTON", "FAVORITE", "DELETE_BUTTON")

    def wait_until_ready(self) -> None:
        self.wait_for_visible(self.NAVIGATION_BAR)
        self.wait_for_visible(self.FAVORITE)

    def shows_text(self, label: str) -> bool:
        """Whether the viewer header shows this exact text (a date, a time, or "Today")."""
        locator = (
            self.By.IOS_PREDICATE,
            f"type == 'XCUIElementTypeStaticText' AND label == {predicate_literal(label)}",
        )
        return self.is_element_visible(locator, timeout=5)

    def is_favorite(self) -> bool:
        return self.find_element(self.FAVORITE).get_attribute("value") == "1"

    def set_favorite(self, favorite: bool) -> None:
        """Tap Favorite once if needed and wait for the switch to report the new state."""
        self.set_switch_state(self.FAVORITE, favorite)

    def delete(self) -> None:
        """Delete and confirm. The photo moves to Recently Deleted, which needs a passcode."""
        self.click(self.DELETE_BUTTON)
        self.click(self.DELETE_CONFIRM)
        self.wait_for_invisible(self.DELETE_CONFIRM)

    def go_back(self) -> PhotosLibraryPage:
        from .photos_library import PhotosLibraryPage

        self.click(self.BACK_BUTTON)
        library = PhotosLibraryPage(self.driver)
        library.wait_until_ready()
        return library
