"""Native Messages composer with explicit unsent-draft cleanup."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base_page import BasePage

if TYPE_CHECKING:
    from .messages_home import MessagesHomePage


class ComposeMessagePage(BasePage):
    """Edit recipient text and message drafts without exposing a send action."""

    NAVIGATION_BAR = (BasePage.By.ACCESSIBILITY_ID, "CKComposeChat")
    RECIPIENT_FIELD = (BasePage.By.ACCESSIBILITY_ID, "To:")
    BODY_FIELD = (BasePage.By.ACCESSIBILITY_ID, "messageBodyField")
    CANCEL_BUTTON = (
        BasePage.By.IOS_CLASS_CHAIN,
        '**/XCUIElementTypeNavigationBar[`name == "CKComposeChat"`]/XCUIElementTypeButton[`name == "Cancel"`]',
    )

    def wait_until_ready(self) -> None:
        """Require the native compose sheet and its editable fields."""
        self.wait_for_visible(self.NAVIGATION_BAR)
        self.wait_for_clickable(self.RECIPIENT_FIELD)
        self.wait_for_clickable(self.BODY_FIELD)
        self.wait_for_clickable(self.CANCEL_BUTTON)

    def _field_value(self, locator: tuple[str, str]) -> str:
        """Normalize UIKit's empty field and placeholder representations."""
        field = self.find_element(locator)
        value = field.get_attribute("value")
        placeholder = field.get_attribute("placeholderValue")
        if value is None or value == placeholder:
            return ""
        if not isinstance(value, str):
            raise AssertionError("Messages field returned a non-text value")
        return value

    def get_recipient(self) -> str:
        """Return uncommitted recipient text from the To field."""
        return self._field_value(self.RECIPIENT_FIELD)

    def set_recipient(self, recipient: str) -> None:
        """Replace recipient text without committing or sending a message.

        Args:
            recipient: Recipient text to enter, or an empty string to clear it.
        """
        self._replace_text(self.RECIPIENT_FIELD, recipient)

    def get_body(self) -> str:
        """Return the current unsent message text."""
        return self._field_value(self.BODY_FIELD)

    def set_body(self, text: str) -> None:
        """Replace draft text and wait for the field to reflect it.

        Args:
            text: Draft text, including Unicode and newlines, or empty to clear.
        """
        self._replace_text(self.BODY_FIELD, text)

    def _replace_text(self, locator: tuple[str, str], text: str) -> None:
        """Clear a field, optionally type text, and verify the resulting value."""
        field = self.wait_for_clickable(locator)
        field.clear()
        if text:
            field.send_keys(text)
        self._get_wait(None).until(lambda _: self._field_value(locator) == text)

    def discard(self) -> MessagesHomePage:
        """Clear this test's draft before closing; safe to call after cancellation."""
        from .messages_home import MessagesHomePage

        if self.is_element_visible(self.NAVIGATION_BAR, timeout=1):
            self.set_body("")
            self.set_recipient("")
            self.click(self.CANCEL_BUTTON)
            self.wait_for_invisible(self.NAVIGATION_BAR)
        home = MessagesHomePage(self.driver)
        home.wait_until_ready()
        return home
