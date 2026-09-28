"""Owned Contacts lifecycle coverage on an explicitly selected simulator."""

from uuid import uuid4

import pytest

from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.pages.contacts import ContactsPage

pytestmark = [pytest.mark.contacts, pytest.mark.lifecycle, pytest.mark.regression]

ContactCase = tuple[ContactsPage, tuple[str, str], tuple[str, str]]


@pytest.fixture
def contact_case(request: pytest.FixtureRequest, lifecycle_simulator: None) -> ContactCase:
    """Register exact-name cleanup after a clean-list check and before creating data."""
    driver = request.getfixturevalue("driver")
    page = ContactsPage(driver)
    request.addfinalizer(lambda: page.launcher.terminate(SystemApps.CONTACTS))
    token = uuid4().hex[:12]
    original = ("UIAutomation", f"{token} Élise O'Connor")
    edited = ("UIAutomation", f"{token} Zoë O'Connor")
    names = (page.full_name(*original), page.full_name(*edited))

    # A collision or an unrelated unsaved editor must fail before registering
    # deletion. This test may only clean up names it was about to create.
    page.relaunch()
    for name in names:
        assert not page.search_contact(name), f"Generated contact already exists: {name!r}"
    page.relaunch()
    request.addfinalizer(lambda: page.cleanup_owned_contacts(names))
    return page, original, edited


def test_contact_create_reopen_edit_delete(contact_case: ContactCase) -> None:
    """Prove Unicode names persist across restarts and deletion persists too."""
    page, original, edited = contact_case
    original_name, edited_name = page.full_name(*original), page.full_name(*edited)

    page.create_contact(*original)
    page.relaunch()
    assert page.search_contact(original_name), "Created contact did not survive relaunch"
    page.open_contact(original_name)

    page.edit_contact(original_name, *edited)
    page.relaunch()
    assert not page.search_contact(original_name), "Old contact name remained after rename"
    assert page.search_contact(edited_name), "Edited contact did not survive relaunch"
    page.open_contact(edited_name)

    page.delete_contact(edited_name)
    page.relaunch()
    assert not page.search_contact(edited_name), "Deleted contact returned after relaunch"
    assert not page.search_contact(original_name), "Original contact remained after lifecycle"
