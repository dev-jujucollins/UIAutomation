"""Contacts search and exact-name lifecycle actions for isolated simulators."""

from __future__ import annotations

from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.utils.app_launcher import AppLauncher
from uiautomation.utils.locators import predicate_literal

from ..base_page import BasePage


class ContactsPage(BasePage):
    """Manage one test-owned contact using the English iOS 27 Contacts UI."""

    SEARCH_FIELD = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeSearchField' AND name == 'Search'",
    )
    ADD_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Add")
    FIRST_NAME = (BasePage.By.ACCESSIBILITY_ID, "First name")
    LAST_NAME = (BasePage.By.ACCESSIBILITY_ID, "Last name")
    DONE_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Done")
    CLOSE_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "close")
    EDIT_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Edit")
    BACK_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "BackButton")
    HEADER = (BasePage.By.ACCESSIBILITY_ID, "ContactCardHeaderView")
    DELETE_ROW = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeCell' AND name == 'Delete Contact'",
    )
    DELETE_SHEET = (BasePage.By.IOS_PREDICATE, "type == 'XCUIElementTypeSheet' AND visible == 1")
    DELETE_CONFIRM = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND name == 'Delete Contact'",
    )
    DISCARD_SHEET = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeSheet' AND ("
        "name == 'Are you sure you want to discard this new contact?' OR "
        "name == 'Are you sure you want to discard your changes?')",
    )
    DISCARD_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Discard Changes")

    def __init__(self, driver: WebDriver, launcher: AppLauncher | None = None) -> None:
        """Bind the driver and optional app-lifecycle helper."""
        super().__init__(driver)
        self.launcher = launcher or AppLauncher(driver)

    def wait_until_ready(self) -> None:
        """Require the contact list's Search and Add controls."""
        self.wait_for_visible(self.SEARCH_FIELD)
        self.wait_for_visible(self.ADD_BUTTON)

    def relaunch(self, *, discard_owned_editor: bool = False) -> None:
        """Restart Contacts and reach its list, optionally discarding an owned editor.

        Args:
            discard_owned_editor: Allow finalizers to discard an editor opened by
                this test, after the initial list state was verified.
        """
        self.launcher.terminate(SystemApps.CONTACTS)
        self.launcher.launch(SystemApps.CONTACTS)
        if self.is_element_visible(self.DONE_BUTTON, timeout=1):
            if not discard_owned_editor:
                raise AssertionError(
                    "Contacts opened with an unsaved editor; refusing to discard it"
                )
            self._discard_owned_editor()
        if self.is_element_visible(self.EDIT_BUTTON, timeout=1):
            self.click(self.BACK_BUTTON)
        self.wait_for_visible(self.SEARCH_FIELD)
        if not self.is_element_visible(self.ADD_BUTTON, timeout=1):
            self.click(self.CLOSE_BUTTON)
        self.wait_until_ready()

    @staticmethod
    def full_name(first_name: str, last_name: str) -> str:
        """Build the expected English contact display name from nonempty fields."""
        if not first_name.strip() or not last_name.strip():
            raise ValueError("Both first and last names are required for lifecycle contacts")
        return f"{first_name} {last_name}"

    @classmethod
    def contact_row(cls, full_name: str) -> tuple[str, str]:
        """Locate exact contact cells without matching other text or photos."""
        return (
            cls.By.IOS_PREDICATE,
            f"type == 'XCUIElementTypeCell' AND name == {predicate_literal(full_name)}",
        )

    def _visible_rows(self, full_name: str) -> list[WebElement]:
        """Exclude hidden backing-list cells retained while search is active."""
        rows = self.driver.find_elements(*self.contact_row(full_name))
        return [row for row in rows if row.is_displayed()]

    def assert_contact_name(self, expected_name: str) -> None:
        """Require the exact saved name before modifying a contact."""
        self.wait_for_attribute(self.HEADER, "label", expected_name)
        self.wait_for_visible(self.EDIT_BUTTON)

    def _set_names(self, first_name: str, last_name: str) -> None:
        """Replace names and confirm native fields retained the supplied Unicode text."""
        self.full_name(first_name, last_name)
        for locator, text in ((self.FIRST_NAME, first_name), (self.LAST_NAME, last_name)):
            self.send_keys(locator, text)
            self.wait_for_attribute(locator, "value", text)

    def create_contact(self, first_name: str, last_name: str) -> None:
        """Create a named contact and verify the saved detail card."""
        expected = self.full_name(first_name, last_name)
        self.wait_until_ready()
        self.click(self.ADD_BUTTON)
        self.wait_for_visible(self.FIRST_NAME)
        self._set_names(first_name, last_name)
        self.click(self.DONE_BUTTON)
        self.assert_contact_name(expected)

    def edit_contact(self, expected_name: str, first_name: str, last_name: str) -> None:
        """Rename only the exact currently open contact and verify the saved name."""
        updated_name = self.full_name(first_name, last_name)
        self.assert_contact_name(expected_name)
        self.click(self.EDIT_BUTTON)
        self.wait_for_visible(self.FIRST_NAME)
        self._set_names(first_name, last_name)
        self.click(self.DONE_BUTTON)
        self.assert_contact_name(updated_name)

    def open_contact(self, full_name: str) -> None:
        """Search and open exactly one visible matching contact, rejecting ambiguity."""
        if not self.search_contact(full_name):
            raise AssertionError(f"Contact not found: {full_name!r}")
        rows = self._visible_rows(full_name)
        if len(rows) != 1:
            raise AssertionError(
                f"Expected one visible contact named {full_name!r}; found {len(rows)}"
            )
        rows[0].click()
        self.assert_contact_name(full_name)

    def search_contact(self, full_name: str) -> bool:
        """Wait for an exact contact search result or the native empty-results state."""
        if not full_name.strip():
            raise ValueError("Contact search requires an exact nonempty name")
        self.send_keys(self.SEARCH_FIELD, full_name)
        self.wait_for_attribute(self.SEARCH_FIELD, "value", full_name)

        def settled(_: WebDriver) -> bool:
            try:
                return bool(self._visible_rows(full_name)) or self._has_no_results(full_name)
            except StaleElementReferenceException:
                return False

        self._get_wait(None).until(settled, f"Contacts search did not settle for {full_name!r}")
        rows = self._visible_rows(full_name)
        if len(rows) > 1:
            raise AssertionError(
                f"Multiple visible contacts named {full_name!r}; refusing to choose"
            )
        return bool(rows)

    def _has_no_results(self, full_name: str) -> bool:
        """Match the query-specific empty state, excluding stale search results."""
        locator = (
            self.By.IOS_PREDICATE,
            "type == 'XCUIElementTypeStaticText' AND name == "
            f"{predicate_literal(f'No Results for “{full_name}”')}",
        )
        return any(element.is_displayed() for element in self.driver.find_elements(*locator))

    def delete_contact(self, expected_name: str) -> None:
        """Delete the exact open contact through its editor and native confirmation."""
        self.assert_contact_name(expected_name)
        self.click(self.EDIT_BUTTON)
        self.wait_for_visible(self.FIRST_NAME)
        first = self.get_attribute(self.FIRST_NAME, "value")
        last = self.get_attribute(self.LAST_NAME, "value")
        if first is None or last is None or self.full_name(first, last) != expected_name:
            raise AssertionError("Contact editor identity changed; refusing to delete")
        for attempt in range(7):
            if self.is_element_visible(self.DELETE_ROW, timeout=1):
                break
            if attempt == 6:
                raise TimeoutException("Delete Contact row did not become visible")
            self.driver.execute_script("mobile: swipe", {"direction": "up"})
        self.click(self.DELETE_ROW)
        sheet = self.wait_for_visible(self.DELETE_SHEET)
        buttons = sheet.find_elements(*self.DELETE_CONFIRM)
        if len(buttons) != 1:
            raise AssertionError("Expected exactly one Delete Contact button in the confirmation")
        # iOS 27 exposes this button as invisible while its parent sheet is
        # visible. The native element click works; never use an unscoped button.
        buttons[0].click()
        self.wait_for_visible(self.SEARCH_FIELD)
        if self.search_contact(expected_name):
            raise AssertionError(f"Deleted contact is still present: {expected_name!r}")

    def _discard_owned_editor(self) -> None:
        """Discard only an editor opened after the test established a clean list."""
        self.click(self.CLOSE_BUTTON)
        self._get_wait(None).until(
            lambda _: self.is_element_visible(self.DISCARD_SHEET, timeout=0)
            or not self.is_element_visible(self.DONE_BUTTON, timeout=0),
            "Contacts editor did not close or present its discard confirmation",
        )
        if self.is_element_visible(self.DISCARD_SHEET, timeout=0):
            sheet = self.find_element(self.DISCARD_SHEET)
            sheet.find_element(*self.DISCARD_BUTTON).click()
        self.wait_for_invisible(self.DONE_BUTTON)

    def cleanup_owned_contacts(self, names: tuple[str, ...]) -> None:
        """Attempt every exact owned name and report cleanup failures to pytest."""
        errors: list[str] = []
        try:
            for name in dict.fromkeys(names):
                try:
                    self.relaunch(discard_owned_editor=True)
                    if self.search_contact(name):
                        self.open_contact(name)
                        self.delete_contact(name)
                except Exception as error:
                    errors.append(f"{name!r}: {error}")
        finally:
            self.launcher.terminate(SystemApps.CONTACTS)
        if errors:
            raise AssertionError("Contacts cleanup failed: " + "; ".join(errors))
