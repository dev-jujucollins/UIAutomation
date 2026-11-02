"""Photos library grid, observed on the English iOS 27.2 simulator."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException

from uiautomation.utils.locators import predicate_literal

from ..base_page import BasePage
from ..system_prompts import answer_system_prompt

if TYPE_CHECKING:
    from .photo_viewer import PhotoViewerPage


class PhotosLibraryPage(BasePage):
    """The Library tab's grid; each photo is an Image labelled "Photo, <date>, <time>".

    Labels use a narrow no-break space (U+202F) before AM/PM, and omit the year for
    photos from the current year.
    """

    LIBRARY_NAV = (BasePage.By.ACCESSIBILITY_ID, "PXCuratedLibraryUIView")
    LIBRARY_TAB = (BasePage.By.ACCESSIBILITY_ID, "LibraryTab")
    COLLECTIONS_TAB = (BasePage.By.ACCESSIBILITY_ID, "CollectionsTab")
    SEARCH_TAB = (BasePage.By.ACCESSIBILITY_ID, "SearchTab")
    LIBRARY_SUMMARY = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeOther' AND label BEGINSWITH 'Library, '",
    )
    PHOTO = (BasePage.By.ACCESSIBILITY_ID, "PXGGridLayout-Info")
    WHATS_NEW_TITLE = (BasePage.By.ACCESSIBILITY_ID, "What’s New in Photos")
    WHATS_NEW_CONTINUE = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND name == 'Continue'",
    )
    LAUNCH_TIMEOUT = 30

    HEALTH_LOCATORS = ("LIBRARY_NAV", "LIBRARY_TAB", "COLLECTIONS_TAB", "SEARCH_TAB")

    def _visible(self, locator: tuple[str, str]) -> WebElement | None:
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return element
            except StaleElementReferenceException:
                continue
        return None

    def wait_until_ready(self) -> None:
        """Get past What's New and permission prompts to a loaded library grid."""

        def ready(_: WebDriver) -> bool:
            try:
                if answer_system_prompt(self.driver, "Photos"):
                    return False
                if self._visible(self.WHATS_NEW_TITLE):
                    button = self._visible(self.WHATS_NEW_CONTINUE)
                    if button:
                        button.click()
                    return False
                if not self._visible(self.LIBRARY_NAV):
                    tab = self._visible(self.LIBRARY_TAB)
                    if tab:
                        tab.click()
                    return False
                return bool(self._visible(self.LIBRARY_SUMMARY))
            except StaleElementReferenceException:
                return False

        self._get_wait(self.LAUNCH_TIMEOUT).until(ready, "Photos library not ready")

    def photo_count(self) -> int:
        """Photos the library reports in its "Library, N Photos" summary."""
        label = str(self.find_element(self.LIBRARY_SUMMARY).get_attribute("label") or "")
        match = re.fullmatch(r"Library, (\d+) Photos?", label)
        if match is None:
            raise AssertionError(f"Unexpected library summary: {label!r}")
        return int(match.group(1))

    def wait_for_count(self, expected: int) -> None:
        def matches(_: WebDriver) -> bool:
            try:
                return self.photo_count() == expected
            except StaleElementReferenceException:
                return False

        self._get_wait(None).until(matches, f"Library never reported {expected} photos")

    def photo_labels(self) -> list[str]:
        """Grid labels in display order (oldest first)."""
        return [str(photo.get_attribute("label") or "") for photo in self.find_elements(self.PHOTO)]

    def open_photo(self, label: str) -> PhotoViewerPage:
        """Open a photo by its exact grid label."""
        from .photo_viewer import PhotoViewerPage

        self.click(
            (
                self.By.IOS_PREDICATE,
                f"name == 'PXGGridLayout-Info' AND label == {predicate_literal(label)}",
            )
        )
        viewer = PhotoViewerPage(self.driver)
        viewer.wait_until_ready()
        return viewer
