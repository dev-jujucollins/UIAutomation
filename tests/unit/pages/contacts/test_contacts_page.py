"""Contacts identity, search, save, and cleanup contracts without an iOS device."""

from unittest.mock import MagicMock, call, patch

import pytest
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.support.wait import WebDriverWait

from tests.integration import test_contacts as integration
from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.pages.contacts import ContactsPage


@pytest.fixture
def page() -> ContactsPage:
    """Use a zero-timeout wait so failed postconditions fail immediately."""
    result = ContactsPage(MagicMock(), launcher=MagicMock())
    result._wait = WebDriverWait(result.driver, 0)
    return result


@pytest.mark.parametrize("first,last", [("", "Last"), ("First", " ")])
def test_blank_names_fail_before_any_action(page: ContactsPage, first: str, last: str) -> None:
    page.click = MagicMock()
    with pytest.raises(ValueError, match="Both first and last"):
        page.create_contact(first, last)
    page.click.assert_not_called()


def test_exact_row_escapes_apostrophes_and_backslashes() -> None:
    _, predicate = ContactsPage.contact_row("UIAutomation Élise O'Connor\\test")
    assert "type == 'XCUIElementTypeCell'" in predicate
    assert "name == 'UIAutomation Élise O\\'Connor\\\\test'" in predicate


def test_search_ignores_hidden_backing_rows(page: ContactsPage) -> None:
    hidden, visible = MagicMock(), MagicMock()
    hidden.is_displayed.return_value = False
    visible.is_displayed.return_value = True
    page.driver.find_elements.return_value = [hidden, visible]
    page.send_keys = MagicMock()
    page.wait_for_attribute = MagicMock()

    assert page.search_contact("UIAutomation Élise")
    page.send_keys.assert_called_once_with(page.SEARCH_FIELD, "UIAutomation Élise")
    page.wait_for_attribute.assert_called_once_with(
        page.SEARCH_FIELD, "value", "UIAutomation Élise"
    )
    hidden.click.assert_not_called()


def test_search_waits_for_query_specific_empty_state(page: ContactsPage) -> None:
    empty = MagicMock()
    page.driver.find_elements.side_effect = (
        lambda strategy, value: [empty] if "No Results for" in value else []
    )
    page.send_keys = MagicMock()
    page.wait_for_attribute = MagicMock()
    assert not page.search_contact("UIAutomation O'Connor")
    predicates = [item.args[1] for item in page.driver.find_elements.call_args_list]
    assert any("No Results for “UIAutomation O\\'Connor”" in value for value in predicates)


def test_search_does_not_treat_transient_empty_rows_as_absence(page: ContactsPage) -> None:
    page.driver.find_elements.return_value = []
    page.send_keys = MagicMock()
    page.wait_for_attribute = MagicMock()
    with pytest.raises(TimeoutException, match="did not settle"):
        page.search_contact("UIAutomation Élise")


def test_search_retries_stale_rows(page: ContactsPage) -> None:
    row = MagicMock()
    page.driver.find_elements.side_effect = [StaleElementReferenceException(), [row], [row]]
    page._wait = WebDriverWait(page.driver, 0.2, poll_frequency=0.001)
    page.send_keys = MagicMock()
    page.wait_for_attribute = MagicMock()
    assert page.search_contact("UIAutomation Élise")


def test_duplicate_visible_contacts_are_never_chosen(page: ContactsPage) -> None:
    rows = [MagicMock(), MagicMock()]
    page.driver.find_elements.return_value = rows
    page.send_keys = MagicMock()
    page.wait_for_attribute = MagicMock()
    with pytest.raises(AssertionError, match="Multiple visible contacts"):
        page.open_contact("UIAutomation Élise")
    assert all(not row.click.called for row in rows)


def test_create_confirms_each_field_before_save(page: ContactsPage) -> None:
    actions = MagicMock()
    page.wait_until_ready = actions.ready
    page.click = actions.click
    page.wait_for_visible = actions.visible
    page.send_keys = actions.type
    page.wait_for_attribute = actions.attribute
    page.assert_contact_name = actions.saved
    page.create_contact("UIAutomation", "Élise O'Connor")
    assert actions.mock_calls == [
        call.ready(),
        call.click(page.ADD_BUTTON),
        call.visible(page.FIRST_NAME),
        call.type(page.FIRST_NAME, "UIAutomation"),
        call.attribute(page.FIRST_NAME, "value", "UIAutomation"),
        call.type(page.LAST_NAME, "Élise O'Connor"),
        call.attribute(page.LAST_NAME, "value", "Élise O'Connor"),
        call.click(page.DONE_BUTTON),
        call.saved("UIAutomation Élise O'Connor"),
    ]


def test_failed_text_entry_cannot_save_a_partial_contact(page: ContactsPage) -> None:
    page.wait_until_ready = MagicMock()
    page.click = MagicMock()
    page.wait_for_visible = MagicMock()
    page.send_keys = MagicMock()
    page.wait_for_attribute = MagicMock(side_effect=TimeoutException())
    with pytest.raises(TimeoutException):
        page.create_contact("UIAutomation", "Élise")
    page.click.assert_called_once_with(page.ADD_BUTTON)


def test_edit_refuses_wrong_contact_before_opening_editor(page: ContactsPage) -> None:
    page.assert_contact_name = MagicMock(side_effect=TimeoutException())
    page.click = MagicMock()
    with pytest.raises(TimeoutException):
        page.edit_contact("UIAutomation Élise", "UIAutomation", "Zoë")
    page.click.assert_not_called()


def test_delete_rechecks_editor_identity_before_destructive_controls(page: ContactsPage) -> None:
    page.assert_contact_name = MagicMock()
    page.click = MagicMock()
    page.wait_for_visible = MagicMock()
    page.get_attribute = MagicMock(side_effect=["Different", "Person"])
    with pytest.raises(AssertionError, match="identity changed"):
        page.delete_contact("UIAutomation Élise")
    page.click.assert_called_once_with(page.EDIT_BUTTON)
    page.driver.execute_script.assert_not_called()


def prepare_delete(page: ContactsPage) -> MagicMock:
    """Set up identity-checked editor and one native confirmation button."""
    page.assert_contact_name = MagicMock()
    page.click = MagicMock()
    page.get_attribute = MagicMock(side_effect=["UIAutomation", "Élise"])
    page.is_element_visible = MagicMock(return_value=True)
    page.search_contact = MagicMock(return_value=False)
    sheet = MagicMock()
    button = MagicMock()
    button.is_displayed.return_value = False
    sheet.find_elements.return_value = [button]
    page.wait_for_visible = MagicMock(return_value=sheet)
    return sheet


def test_delete_scopes_native_confirmation_and_verifies_absence(page: ContactsPage) -> None:
    sheet = prepare_delete(page)
    page.delete_contact("UIAutomation Élise")
    sheet.find_elements.assert_called_once_with(*page.DELETE_CONFIRM)
    sheet.find_elements.return_value[0].click.assert_called_once_with()
    page.search_contact.assert_called_once_with("UIAutomation Élise")
    page.click.assert_has_calls([call(page.EDIT_BUTTON), call(page.DELETE_ROW)])


def test_delete_refuses_ambiguous_confirmation(page: ContactsPage) -> None:
    sheet = prepare_delete(page)
    buttons = [MagicMock(), MagicMock()]
    sheet.find_elements.return_value = buttons
    with pytest.raises(AssertionError, match="exactly one Delete Contact"):
        page.delete_contact("UIAutomation Élise")
    assert all(not button.click.called for button in buttons)


def test_missing_delete_row_has_bounded_scroll_and_no_confirmation(page: ContactsPage) -> None:
    sheet = prepare_delete(page)
    page.is_element_visible = MagicMock(return_value=False)
    with pytest.raises(TimeoutException, match="Delete Contact row"):
        page.delete_contact("UIAutomation Élise")
    assert page.driver.execute_script.call_count == 6
    page.click.assert_called_once_with(page.EDIT_BUTTON)
    sheet.find_elements.assert_not_called()


def test_delete_fails_when_contact_still_exists(page: ContactsPage) -> None:
    prepare_delete(page)
    page.search_contact = MagicMock(return_value=True)
    with pytest.raises(AssertionError, match="still present"):
        page.delete_contact("UIAutomation Élise")


def test_relaunch_refuses_an_unowned_unsaved_editor(page: ContactsPage) -> None:
    page.is_element_visible = MagicMock(return_value=True)
    page.click = MagicMock()
    with pytest.raises(AssertionError, match="unsaved editor"):
        page.relaunch()
    page.click.assert_not_called()


def test_owned_draft_discard_requires_known_sheet_and_scopes_button(page: ContactsPage) -> None:
    page.click = MagicMock()
    page.is_element_visible = MagicMock(return_value=True)
    page.find_element = MagicMock()
    page.wait_for_invisible = MagicMock()
    page._discard_owned_editor()
    page.find_element.assert_called_once_with(page.DISCARD_SHEET)
    page.find_element.return_value.find_element.assert_called_once_with(*page.DISCARD_BUTTON)
    page.find_element.return_value.find_element.return_value.click.assert_called_once_with()
    assert "discard this new contact" in page.DISCARD_SHEET[1]
    assert "discard your changes" in page.DISCARD_SHEET[1]


def test_unknown_discard_prompt_never_gets_confirmed(page: ContactsPage) -> None:
    page.click = MagicMock()
    page.is_element_visible = MagicMock(
        side_effect=lambda locator, timeout: locator == page.DONE_BUTTON
    )
    page.find_element = MagicMock()
    with pytest.raises(TimeoutException, match="did not close"):
        page._discard_owned_editor()
    page.find_element.assert_not_called()


def test_cleanup_attempts_all_exact_names_and_reports_failure(page: ContactsPage) -> None:
    page.relaunch = MagicMock()
    page.search_contact = MagicMock(return_value=True)
    page.open_contact = MagicMock()
    page.delete_contact = MagicMock(side_effect=[TimeoutException("failed"), None])
    with pytest.raises(AssertionError, match="Contacts cleanup failed"):
        page.cleanup_owned_contacts(("Original", "Edited", "Original"))
    assert page.delete_contact.call_args_list == [call("Original"), call("Edited")]
    page.launcher.terminate.assert_called_once_with(SystemApps.CONTACTS)


def test_cleanup_does_not_open_or_delete_absent_contacts(page: ContactsPage) -> None:
    page.relaunch = MagicMock()
    page.search_contact = MagicMock(return_value=False)
    page.open_contact = MagicMock()
    page.delete_contact = MagicMock()
    page.cleanup_owned_contacts(("Original", "Edited"))
    page.open_contact.assert_not_called()
    page.delete_contact.assert_not_called()


def test_case_registers_owned_cleanup_before_test_can_create_contact() -> None:
    request, page = MagicMock(), MagicMock()
    page.full_name.side_effect = ContactsPage.full_name
    page.search_contact.return_value = False
    with patch.object(integration, "ContactsPage", return_value=page):
        result = integration.contact_case.__wrapped__(request, None)
    assert result[0] is page
    page.create_contact.assert_not_called()
    request.addfinalizer.call_args_list[-1].args[0]()
    original, edited = result[1:]
    page.cleanup_owned_contacts.assert_called_once_with(
        (ContactsPage.full_name(*original), ContactsPage.full_name(*edited))
    )


def test_existing_name_collision_never_registers_deletion() -> None:
    request, page = MagicMock(), MagicMock()
    page.full_name.side_effect = ContactsPage.full_name
    page.search_contact.return_value = True
    with patch.object(integration, "ContactsPage", return_value=page):
        with pytest.raises(AssertionError, match="already exists"):
            integration.contact_case.__wrapped__(request, None)
    assert request.addfinalizer.call_count == 1
    request.addfinalizer.call_args.args[0]()
    page.cleanup_owned_contacts.assert_not_called()
    page.launcher.terminate.assert_called_once_with(SystemApps.CONTACTS)
