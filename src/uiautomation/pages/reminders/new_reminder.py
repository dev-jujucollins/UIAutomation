"""New Reminder sheet opened from the Reminders lists overview."""

from __future__ import annotations

from typing import TYPE_CHECKING

from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import StaleElementReferenceException

from ..base_page import BasePage

if TYPE_CHECKING:
    from .reminders_home import RemindersHomePage


class NewReminderPage(BasePage):
    """Create or discard one reminder through the sheet."""

    # The overview's "New Reminder" button shares the name, so match the bar itself.
    NAVIGATION_BAR = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeNavigationBar' AND name == 'New Reminder'",
    )
    TITLE_FIELD = (BasePage.By.ACCESSIBILITY_ID, "Quick Entry Title Field")
    NOTES_FIELD = (BasePage.By.ACCESSIBILITY_ID, "Notes text view")
    DONE_BUTTON = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND name == 'Done'",
    )
    CANCEL_BUTTON = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND name == 'Cancel'",
    )
    # Cancel with a typed title asks "Are you sure you want to discard this new reminder?"
    DISCARD_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Discard Changes")

    HEALTH_LOCATORS = ("NAVIGATION_BAR", "TITLE_FIELD", "NOTES_FIELD", "DONE_BUTTON")

    def wait_until_ready(self) -> None:
        """Require the sheet and its editable title."""
        self.wait_for_visible(self.NAVIGATION_BAR)
        self.wait_for_clickable(self.TITLE_FIELD)

    def set_title(self, title: str) -> None:
        """Type a title and wait until the field reports it."""
        if "," in title:
            # Rows are labelled "<title>, <state>"; a comma would make that ambiguous.
            raise ValueError("Reminder titles used by tests must not contain commas")
        self.send_keys(self.TITLE_FIELD, title, clear_first=True)
        self.wait_for_attribute(self.TITLE_FIELD, "value", title)

    def save(self) -> RemindersHomePage:
        """Add the reminder and return to the overview."""
        from .reminders_home import RemindersHomePage

        self.click(self.DONE_BUTTON)
        self.wait_for_invisible(self.NAVIGATION_BAR)
        return RemindersHomePage(self.driver)

    def is_open(self) -> bool:
        return bool(self.driver.find_elements(*self.NAVIGATION_BAR))

    def discard(self) -> None:
        """Cancel the sheet, confirming the discard prompt if a title was typed.

        Safe to call when the sheet is already closed, so it can be a finalizer.
        """
        from .reminders_home import RemindersHomePage

        clicked: set[str] = set()

        def closed(_: WebDriver) -> bool:
            try:
                for locator in (self.DISCARD_BUTTON, self.CANCEL_BUTTON):
                    buttons = [
                        button
                        for button in self.driver.find_elements(*locator)
                        if button.is_displayed()
                    ]
                    if buttons:
                        # Tap each control once; the sheet animates before it disappears.
                        if buttons[0].id not in clicked:
                            clicked.add(buttons[0].id)
                            buttons[0].click()
                        return False
                return not self.is_open()
            except StaleElementReferenceException:
                return False

        self._get_wait(None).until(closed, "New Reminder sheet did not close")
        RemindersHomePage(self.driver).wait_until_ready()
