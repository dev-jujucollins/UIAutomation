"""The local site server serves its folder and stops cleanly."""

from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from uiautomation.utils.local_site import serve_directory

SITE = Path(__file__).resolve().parents[1] / "integration" / "fixtures" / "site"


def test_serves_fixture_pages_on_loopback() -> None:
    with serve_directory(SITE) as url:
        assert url.startswith("http://127.0.0.1:")
        with urlopen(url + "second.html", timeout=5) as response:  # noqa: S310
            assert b"Second fixture page" in response.read()
    with pytest.raises(URLError):
        urlopen(url, timeout=2)  # noqa: S310


def test_missing_folder_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        with serve_directory(tmp_path / "missing"):
            pass
