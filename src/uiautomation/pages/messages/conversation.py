"""Read-only navigation within an existing Messages conversation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base_page import BasePage

if TYPE_CHECKING:
    from .messages_home import MessagesHomePage


class ConversationPage(BasePage):
    """Inspect a conversation and return to its list without sending messages."""

    TITLE = (BasePage.By.ACCESSIBILITY_ID, "ConversationTitle")
    BODY_FIELD = (BasePage.By.ACCESSIBILITY_ID, "messageBodyField")
    BACK_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "BackButton")
    TRANSCRIPT = (BasePage.By.ACCESSIBILITY_ID, "TranscriptCollectionView")

    def wait_until_ready(self) -> None:
        """Require conversation title, draft field, transcript, and back control."""
        self.wait_for_visible(self.TITLE)
        self.wait_for_visible(self.BODY_FIELD)
        self.wait_for_clickable(self.BACK_BUTTON)
        self.find_element(self.TRANSCRIPT)

    def get_recipient(self) -> str:
        """Return the conversation header's displayed recipient."""
        value = self.get_attribute(self.TITLE, "label")
        if not value or not value.strip():
            raise AssertionError("Conversation recipient is empty")
        return value

    def go_back(self) -> MessagesHomePage:
        """Return to Messages home and wait for the transition to finish."""
        from .messages_home import MessagesHomePage

        self.click(self.BACK_BUTTON)
        self.wait_for_invisible(self.BODY_FIELD)
        home = MessagesHomePage(self.driver)
        home.wait_until_ready()
        return home
