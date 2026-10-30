"""WebDriverAgent builds are reused only for the versions that produced them."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from uiautomation.utils import wda_setup
from uiautomation.utils.wda_setup import BUILD_STAMP, ensure_prebuilt_wda, has_prebuilt_wda

IDENTITY = {"webdriveragent": "16.17.6", "xcode": "Xcode 27.2\nBuild version 27B52"}


@pytest.fixture(autouse=True)
def identity():
    with patch.object(wda_setup, "wda_build_identity", return_value=dict(IDENTITY)) as mock:
        yield mock


def _built(root: Path, stamp: dict | None) -> Path:
    app = root / "Build" / "Products" / "Debug-iphonesimulator" / wda_setup.WDA_RUNNER_APP
    app.mkdir(parents=True)
    if stamp is not None:
        (root / BUILD_STAMP).write_text(json.dumps(stamp))
    return root


def test_wda_build_is_bounded_and_stamped(tmp_path: Path) -> None:
    """A stalled build must have a finite deadline; a finished one records its versions."""
    with patch.object(wda_setup.subprocess, "run") as run:
        ensure_prebuilt_wda(tmp_path)
    assert run.call_args.kwargs["timeout"] == 600
    assert json.loads((tmp_path / BUILD_STAMP).read_text()) == IDENTITY


def test_matching_build_is_reused(tmp_path: Path) -> None:
    _built(tmp_path, IDENTITY)
    with patch.object(wda_setup.subprocess, "run") as run:
        ensure_prebuilt_wda(tmp_path)
    run.assert_not_called()


@pytest.mark.parametrize(
    "stamp", [None, {**IDENTITY, "xcode": "Xcode 26.4"}, {**IDENTITY, "webdriveragent": "9.0.0"}]
)
def test_unstamped_or_outdated_build_is_rebuilt(tmp_path: Path, stamp: dict | None) -> None:
    _built(tmp_path, stamp)
    assert not has_prebuilt_wda(tmp_path)
    with patch.object(wda_setup.subprocess, "run") as run:
        ensure_prebuilt_wda(tmp_path)
    run.assert_called_once()


def test_failed_build_leaves_no_stamp(tmp_path: Path) -> None:
    _built(tmp_path, {**IDENTITY, "xcode": "old"})
    with patch.object(wda_setup.subprocess, "run", side_effect=OSError("xcodebuild failed")):
        with pytest.raises(OSError):
            ensure_prebuilt_wda(tmp_path)
    assert not (tmp_path / BUILD_STAMP).exists()
