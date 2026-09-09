"""Tests for optional WebDriverAgent builds."""

from pathlib import Path
from unittest.mock import patch

from uiautomation.utils.wda_setup import ensure_prebuilt_wda


def test_wda_build_is_bounded(tmp_path: Path) -> None:
    """A stalled optional build must have a finite deadline."""
    with patch("uiautomation.utils.wda_setup.subprocess.run") as run:
        ensure_prebuilt_wda(tmp_path)
        assert run.call_args.kwargs["timeout"] == 600
