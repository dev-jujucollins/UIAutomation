"""Photos library and viewer on the simulator's sample photos, plus one imported photo."""

import struct
import zlib
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.pages.photos import PhotosLibraryPage
from uiautomation.utils.app_launcher import AppLauncher
from uiautomation.utils.simulator_control import add_media

pytestmark = pytest.mark.photos


def _viewer_date(grid_label: str) -> str:
    """'Photo, October 09, 2009, 2:09 PM' -> the viewer's 'October 9, 2009'."""
    date = datetime.strptime(", ".join(grid_label.split(", ")[1:3]), "%B %d, %Y")
    return f"{date:%B} {date.day}, {date.year}"


def _png(path: Path, rgb: tuple[int, int, int], size: int = 64) -> Path:
    """Write a solid-colour PNG without EXIF, so Photos dates it at import."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    pixels = b"".join(b"\x00" + bytes(rgb) * size for _ in range(size))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )
    return path


@pytest.mark.smoke
def test_photos_library_is_ready(photos_library: PhotosLibraryPage) -> None:
    """Photos reaches its Library grid past What's New and permission prompts."""
    assert photos_library.photo_count() == len(photos_library.photo_labels())


@pytest.mark.journey
def test_open_photo_shows_its_date_and_returns(photos_library: PhotosLibraryPage) -> None:
    """A sample photo opens in the viewer with its capture date; Back returns to the grid."""
    labels = photos_library.photo_labels()
    dated = [label for label in labels if label.count(", ") >= 3]  # has a year: not this year
    assert dated, "Expected the simulator's sample photos"
    viewer = photos_library.open_photo(dated[0])
    assert viewer.shows_text(_viewer_date(dated[0]))
    viewer.go_back()


@pytest.mark.lifecycle
@pytest.mark.regression
def test_imported_photo_favorite_and_delete(
    request: pytest.FixtureRequest, lifecycle_simulator: None, tmp_path: Path
) -> None:
    """An imported photo appears, toggles Favorite, and leaves the library when deleted.

    Deleted photos stay in Recently Deleted for 30 days; that album needs a passcode,
    so tests cannot empty it. Run this only on a disposable, named simulator.
    """
    library: PhotosLibraryPage = request.getfixturevalue("photos_library")
    launcher = AppLauncher(library.driver)

    def relaunch() -> PhotosLibraryPage:
        # The open grid does not pick up simctl imports; a relaunch reloads the library.
        launcher.terminate(SystemApps.PHOTOS)
        launcher.launch(SystemApps.PHOTOS)
        library.wait_until_ready()
        return library

    before_labels = set(library.photo_labels())
    before = library.photo_count()

    def remove_imported() -> None:
        # Only photos absent before the import are this test's; delete those.
        relaunch()
        for label in library.photo_labels():
            if label not in before_labels:
                library.open_photo(label).delete()
                relaunch()

    # Registered before importing, so a failure at any later step still cleans up.
    request.addfinalizer(remove_imported)
    seed = uuid4().bytes
    add_media(library.driver.capabilities["udid"], _png(tmp_path / "owned.png", tuple(seed[:3])))
    relaunch().wait_for_count(before + 1)

    added = [label for label in library.photo_labels() if label not in before_labels]
    assert len(added) == 1, f"Expected exactly one new photo, found {added}"
    owned = added[0]

    viewer = library.open_photo(owned)
    assert viewer.shows_text("Today")
    viewer.set_favorite(True)
    viewer.set_favorite(False)
    viewer.delete()
    viewer.go_back()
    relaunch().wait_for_count(before)
    assert owned not in library.photo_labels()
