"""Messages draft and navigation tests; no test sends a message."""

import pytest

from uiautomation.pages.messages import ComposeMessagePage, MessagesHomePage

pytestmark = pytest.mark.messages
TEST_RECIPIENT = "2025550123"


@pytest.mark.smoke
def test_messages_home_is_ready(messages_home: MessagesHomePage) -> None:
    """Verify Messages exposes usable list and search controls."""
    messages_home.wait_until_ready()


@pytest.mark.smoke
def test_open_composer_and_cancel(message_draft: ComposeMessagePage) -> None:
    """An empty composer closes completely and returns to Messages home."""
    message_draft.wait_until_ready()
    assert message_draft.get_recipient() == ""
    assert message_draft.get_body() == ""
    message_draft.discard().wait_until_ready()


def test_enter_and_remove_recipient(message_draft: ComposeMessagePage) -> None:
    """Recipient text can be edited and removed before committing it."""
    message_draft.set_recipient(TEST_RECIPIENT)
    assert message_draft.get_recipient() == TEST_RECIPIENT
    message_draft.set_recipient("")
    assert message_draft.get_recipient() == ""


@pytest.mark.parametrize(
    "text",
    ["UIAutomation draft", "UIAutomation café 🙂", "First line\nSecond line"],
    ids=["plain", "unicode", "multiline"],
)
def test_edit_and_clear_draft(message_draft: ComposeMessagePage, text: str) -> None:
    """Draft editing preserves entered characters and clears to empty."""
    message_draft.set_body(text)
    assert message_draft.get_body() == text
    message_draft.set_body("Replacement draft")
    assert message_draft.get_body() == "Replacement draft"
    message_draft.set_body("")
    assert message_draft.get_body() == ""


@pytest.mark.journey
def test_draft_discard_round_trip(
    messages_home: MessagesHomePage, message_draft: ComposeMessagePage
) -> None:
    """Discard recipient and text, then verify a reopened composer is empty."""
    message_draft.set_recipient(TEST_RECIPIENT)
    message_draft.set_body("UIAutomation unsent draft")
    assert message_draft.get_body() == "UIAutomation unsent draft"
    message_draft.discard()
    reopened = messages_home.open_compose()
    # The draft fixture's finalizer also owns this composer on the same driver.
    assert reopened.get_recipient() == ""
    assert reopened.get_body() == ""
    reopened.discard()


@pytest.mark.journey
def test_existing_conversation_round_trip(messages_home: MessagesHomePage) -> None:
    """Open simulator seed data and return without modifying its draft."""
    conversation = messages_home.open_first_conversation()
    assert conversation.get_recipient()
    conversation.go_back().wait_until_ready()
