"""Files app locations and folders, observed on the English iOS 27.2 simulator."""

from __future__ import annotations

from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException

from uiautomation.utils.locators import predicate_literal

from ..base_page import BasePage
from ..system_prompts import answer_system_prompt


class FilesPage(BasePage):
    """Browse locations and create, rename, delete, and purge folders.

    Folder cells are named "<name>, Folder". Deleting moves a folder to Recently Deleted,
    which is not passcode-locked, so tests can remove their folders completely.
    """

    NAVIGATION_BAR = (
        BasePage.By.ACCESSIBILITY_ID,
        "FullDocumentManagerViewControllerNavigationBar",
    )
    BROWSE_TAB = (BasePage.By.ACCESSIBILITY_ID, "Browse")
    RECENTS_TAB = (BasePage.By.ACCESSIBILITY_ID, "Recents")
    SEARCH_FIELD = (BasePage.By.IOS_PREDICATE, "type == 'XCUIElementTypeSearchField'")
    MORE_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "TopOverflowBarButtonItem")
    NEW_FOLDER = (BasePage.By.ACCESSIBILITY_ID, "New Folder")
    RENAME_FIELD = (BasePage.By.ACCESSIBILITY_ID, "DOC.inlineRenameField")
    DONE_BUTTON = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND name == 'Done'",
    )
    MENU_RENAME = (BasePage.By.ACCESSIBILITY_ID, "Rename")
    MENU_DELETE = (BasePage.By.ACCESSIBILITY_ID, "Delete")
    MENU_DELETE_NOW = (BasePage.By.ACCESSIBILITY_ID, "Delete Now")
    ALERT = (BasePage.By.CLASS_NAME, "XCUIElementTypeAlert")
    ON_MY_IPHONE = "On My iPhone"
    RECENTLY_DELETED = "Recently Deleted"
    LAUNCH_TIMEOUT = 30

    HEALTH_LOCATORS = ("NAVIGATION_BAR", "BROWSE_TAB", "RECENTS_TAB", "SEARCH_FIELD")

    def _visible(self, locator: tuple[str, str]) -> WebElement | None:
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return element
            except StaleElementReferenceException:
                continue
        return None

    def wait_until_ready(self) -> None:
        """Require the document browser and its tabs."""

        def ready(_: WebDriver) -> bool:
            try:
                if answer_system_prompt(self.driver, "Files"):
                    return False
                return bool(self._visible(self.NAVIGATION_BAR) and self._visible(self.BROWSE_TAB))
            except StaleElementReferenceException:
                return False

        self._get_wait(self.LAUNCH_TIMEOUT).until(ready, "Files browser not ready")

    @staticmethod
    def location_item(name: str) -> tuple[str, str]:
        return (BasePage.By.ACCESSIBILITY_ID, f"DOC.sidebar.item.{name}")

    @staticmethod
    def folder(name: str) -> tuple[str, str]:
        return (BasePage.By.ACCESSIBILITY_ID, f"{name}, Folder")

    def open_location(self, name: str) -> None:
        """Open a Browse location such as On My iPhone or Recently Deleted.

        Browse reopens the last location; tapping it again shows the locations list.
        """
        title = (
            self.By.IOS_PREDICATE,
            f"type == 'XCUIElementTypeStaticText' AND label == {predicate_literal(name)}",
        )
        tapped: set[str] = set()

        def opened(_: WebDriver) -> bool:
            try:
                item = self._visible(self.location_item(name))
                if item is not None:
                    item.click()
                    return False
                if self._visible(title) and not self._visible(self.location_item(name)):
                    return True
                browse = self._visible(self.BROWSE_TAB)
                if browse is not None and browse.id not in tapped:
                    tapped.add(browse.id)
                    browse.click()
                else:
                    tapped.clear()
                return False
            except StaleElementReferenceException:
                return False

        self._get_wait(None).until(opened, f"Files location {name!r} did not open")

    def has_folder(self, name: str) -> bool:
        return bool(self.driver.find_elements(*self.folder(name)))

    def wait_for_folder(self, name: str, present: bool = True) -> None:
        self._get_wait(None).until(
            lambda _: self.has_folder(name) == present,
            f"Folder {name!r} never became {'present' if present else 'absent'}",
        )

    def _set_inline_name(self, name: str) -> None:
        if "," in name:
            # Cells are named "<name>, Folder"; a comma would make that ambiguous.
            raise ValueError("Folder names used by tests must not contain commas")
        field = self.wait_for_visible(self.RENAME_FIELD)
        field.clear()
        field.send_keys(name)
        self.click(self.DONE_BUTTON)
        self.wait_for_folder(name)

    def create_folder(self, name: str) -> None:
        """Create a folder in the current location (More → New Folder) and name it."""
        self.click(self.MORE_BUTTON)
        self.click(self.NEW_FOLDER)
        self._set_inline_name(name)

    def _menu(self, name: str, action: tuple[str, str]) -> None:
        """Long-press a folder and choose a context-menu action."""
        cell = self.find_element(self.folder(name))
        self.driver.execute_script("mobile: touchAndHold", {"elementId": cell.id, "duration": 1.0})
        self.click(action)

    def rename_folder(self, old: str, new: str) -> None:
        self._menu(old, self.MENU_RENAME)
        self._set_inline_name(new)
        self.wait_for_folder(old, present=False)

    def delete_folder(self, name: str) -> None:
        """Move a folder to Recently Deleted; Files does not confirm."""
        self._menu(name, self.MENU_DELETE)
        self.wait_for_folder(name, present=False)

    def purge_folder(self, name: str) -> None:
        """Permanently delete a folder from Recently Deleted (the current location).

        The confirmation names the item; it is confirmed only when it names this folder.
        """
        self._menu(name, self.MENU_DELETE_NOW)
        alert = self.wait_for_visible(self.ALERT)
        title = str(alert.get_attribute("label") or "")
        if title != f"Are you sure you want to delete “{name}”?":
            raise AssertionError(f"Unexpected Files delete confirmation: {title!r}")
        alert.find_element(
            self.By.IOS_PREDICATE, "type == 'XCUIElementTypeButton' AND label == 'Delete'"
        ).click()
        self.wait_for_folder(name, present=False)
