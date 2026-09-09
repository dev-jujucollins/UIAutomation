"""Tests for failure artifacts."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from uiautomation.utils.failure_artifacts import capture_failure


def test_failed_screenshot_does_not_hide_other_evidence(tmp_path: Path) -> None:
    """A broken screenshot must not prevent XML, logs, or error capture."""
    driver = MagicMock()
    driver.save_screenshot.side_effect = RuntimeError("disconnected")
    driver.page_source = "<Application/>"
    log = tmp_path / "server.log"
    log.write_text("server error", encoding="utf-8")
    output = capture_failure(tmp_path, "test[param/one]", "setup", driver, log, "failure")
    assert (output / "page.xml").read_text() == "<Application/>"
    assert (output / "appium.log").read_text() == "server error"
    assert "disconnected" in (output / "failure.json").read_text()
    second = capture_failure(tmp_path, "test[param/one]", "setup", None, None, "failure")
    assert output != second
    assert json.loads((second / "failure.json").read_text())["capture_errors"]
