"""Messages navigation and test-owned draft cleanup contracts."""

from unittest.mock import MagicMock, call, patch

import pytest
from selenium.common.exceptions import TimeoutException

import conftest
from uiautomation.pages.messages import ComposeMessagePage, ConversationPage, MessagesHomePage


@pytest.mark.parametrize(
    "value, placeholder, expected",
    [
        (None, "", ""),
        ("", "", ""),
        ("iMessage", "iMessage", ""),
        ("Hello 🙂\nWorld", "", "Hello 🙂\nWorld"),
    ],
)
def test_draft_text_values(value, placeholder, expected: str) -> None:
    page = ComposeMessagePage(MagicMock())
    field = MagicMock()
    field.get_attribute.side_effect = lambda key: {"value": value, "placeholderValue": placeholder}[
        key
    ]
    page.find_element = MagicMock(return_value=field)
    assert page.get_body() == expected


def test_nontext_value_fails_instead_of_passing_as_empty() -> None:
    page = ComposeMessagePage(MagicMock())
    field = MagicMock()
    field.get_attribute.side_effect = [{"unexpected": "value"}, ""]
    page.find_element = MagicMock(return_value=field)
    with pytest.raises(AssertionError, match="non-text"):
        page.get_body()


@pytest.mark.parametrize("text", ["", "Unsent 🙂\nDraft"])
def test_replace_text_clears_before_typing_and_checks_result(text: str) -> None:
    page = ComposeMessagePage(MagicMock())
    field = MagicMock()
    page.wait_for_clickable = MagicMock(return_value=field)
    page._field_value = MagicMock(return_value=text)
    page.set_body(text)
    expected = [call.clear()] + ([call.send_keys(text)] if text else [])
    assert field.mock_calls == expected
    page._field_value.assert_called_with(page.BODY_FIELD)


def test_failed_text_entry_cannot_silently_pass() -> None:
    page = ComposeMessagePage(MagicMock())
    page.DEFAULT_TIMEOUT = 0
    page.wait_for_clickable = MagicMock()
    page._field_value = MagicMock(return_value="wrong text")
    with pytest.raises(TimeoutException):
        page.set_body("expected")


def test_discard_clears_fields_before_cancel_and_waits_for_home() -> None:
    page = ComposeMessagePage(MagicMock())
    actions = MagicMock()
    page.is_element_visible = MagicMock(return_value=True)
    page.set_body = actions.body
    page.set_recipient = actions.recipient
    page.click = actions.click
    page.wait_for_invisible = actions.closed
    with patch.object(MessagesHomePage, "wait_until_ready", actions.home):
        page.discard()
    assert actions.mock_calls == [
        call.body(""),
        call.recipient(""),
        call.click(page.CANCEL_BUTTON),
        call.closed(page.NAVIGATION_BAR),
        call.home(),
    ]


def test_discard_after_cancel_does_not_touch_other_fields() -> None:
    page = ComposeMessagePage(MagicMock())
    page.is_element_visible = MagicMock(return_value=False)
    page.set_body = MagicMock()
    page.set_recipient = MagicMock()
    with patch.object(MessagesHomePage, "wait_until_ready") as ready:
        page.discard()
    page.set_body.assert_not_called()
    page.set_recipient.assert_not_called()
    ready.assert_called_once_with()


def test_failed_draft_cleanup_does_not_hide_loss_of_text_control() -> None:
    page = ComposeMessagePage(MagicMock())
    page.is_element_visible = MagicMock(return_value=True)
    page.set_body = MagicMock(side_effect=TimeoutException())
    page.click = MagicMock()
    with pytest.raises(TimeoutException):
        page.discard()
    page.click.assert_not_called()


def test_compose_uses_empty_sms_link_and_waits_for_ready_fields() -> None:
    home = MessagesHomePage(MagicMock())
    home.wait_until_ready = MagicMock()
    with patch.object(ComposeMessagePage, "wait_until_ready") as ready:
        result = home.open_compose()
    home.driver.execute_script.assert_called_once_with(
        "mobile: deepLink", {"url": "sms:", "bundleId": "com.apple.MobileSMS"}
    )
    assert isinstance(result, ComposeMessagePage)
    ready.assert_called_once_with()


def test_missing_seed_data_is_a_failure() -> None:
    home = MessagesHomePage(MagicMock())
    home.wait_until_ready = MagicMock()
    home.driver.find_elements.return_value = []
    with pytest.raises(AssertionError, match="seeded conversation"):
        home.open_first_conversation()


def test_open_conversation_ignores_hidden_rows() -> None:
    home = MessagesHomePage(MagicMock())
    home.wait_until_ready = MagicMock()
    hidden, visible = MagicMock(), MagicMock()
    hidden.is_displayed.return_value = False
    visible.is_displayed.return_value = True
    home.driver.find_elements.return_value = [hidden, visible]
    with patch.object(ConversationPage, "wait_until_ready"):
        home.open_first_conversation()
    hidden.click.assert_not_called()
    visible.click.assert_called_once_with()


def test_draft_finalizer_is_registered_before_open_failure() -> None:
    request, home = MagicMock(), MagicMock()
    home.open_compose.side_effect = TimeoutException()
    with pytest.raises(TimeoutException):
        conftest.message_draft.__wrapped__(request, home)
    cleanup = request.addfinalizer.call_args.args[0]
    assert isinstance(cleanup.__self__, ComposeMessagePage)
    assert cleanup.__self__.driver is home.driver


def test_messages_termination_registered_before_launch_failure() -> None:
    request, driver, launcher = MagicMock(), MagicMock(), MagicMock()
    launcher.launch.side_effect = RuntimeError("launch failed")
    fixture = conftest.messages_home.__wrapped__(request, driver, launcher)
    with pytest.raises(RuntimeError, match="launch failed"):
        next(fixture)
    cleanup = request.addfinalizer.call_args.args[0]
    launcher.terminate.reset_mock()
    cleanup()
    launcher.terminate.assert_called_once_with(conftest.SystemApps.MESSAGES)
