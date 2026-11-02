"""Files locations, plus one owned folder created, renamed, deleted, and purged."""

from uuid import uuid4

import pytest

from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.pages.files import FilesPage
from uiautomation.utils.app_launcher import AppLauncher

pytestmark = pytest.mark.files


@pytest.mark.smoke
def test_files_browser_is_ready(files_home: FilesPage) -> None:
    """Files reaches its document browser."""
    assert files_home.is_element_visible(files_home.SEARCH_FIELD)


@pytest.mark.journey
def test_browse_on_my_iphone_and_recently_deleted(files_home: FilesPage) -> None:
    """Both local locations open from Browse."""
    files_home.open_location(files_home.ON_MY_IPHONE)
    files_home.open_location(files_home.RECENTLY_DELETED)


def _relaunch(page: FilesPage) -> FilesPage:
    """Restart Files so checks read the file system, not the current screen."""
    launcher = AppLauncher(page.driver)
    launcher.terminate(SystemApps.FILES)
    launcher.launch(SystemApps.FILES)
    page.wait_until_ready()
    return page


def _remove_completely(page: FilesPage, names: tuple[str, ...]) -> None:
    """Delete and purge only these generated folder names, wherever they are."""
    _relaunch(page)
    page.open_location(page.ON_MY_IPHONE)
    for name in names:
        if page.has_folder(name):
            page.delete_folder(name)
    page.open_location(page.RECENTLY_DELETED)
    for name in names:
        if page.has_folder(name):
            page.purge_folder(name)


@pytest.mark.lifecycle
@pytest.mark.regression
def test_folder_create_rename_delete_purge(
    request: pytest.FixtureRequest, lifecycle_simulator: None
) -> None:
    """A folder persists across relaunches, renames, and is removed completely."""
    page: FilesPage = request.getfixturevalue("files_home")
    token = uuid4().hex[:12]
    original, renamed = f"UIAutomation {token}", f"UIAutomation {token} renamed"
    page.open_location(page.ON_MY_IPHONE)
    assert not page.has_folder(original) and not page.has_folder(renamed)
    # Registered before creating: cleanup touches only these two generated names.
    request.addfinalizer(lambda: _remove_completely(page, (original, renamed)))

    page.create_folder(original)
    _relaunch(page).open_location(page.ON_MY_IPHONE)
    assert page.has_folder(original), "Created folder did not survive relaunch"

    page.rename_folder(original, renamed)
    _relaunch(page).open_location(page.ON_MY_IPHONE)
    assert page.has_folder(renamed) and not page.has_folder(original)

    page.delete_folder(renamed)
    page.open_location(page.RECENTLY_DELETED)
    assert page.has_folder(renamed), "Deleted folder missing from Recently Deleted"
    page.purge_folder(renamed)

    _relaunch(page).open_location(page.ON_MY_IPHONE)
    assert not page.has_folder(renamed)
    page.open_location(page.RECENTLY_DELETED)
    assert not page.has_folder(renamed)
