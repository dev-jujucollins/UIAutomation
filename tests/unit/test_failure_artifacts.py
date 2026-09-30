"""Tests for failure artifacts."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from uiautomation.utils.failure_artifacts import artifact_links, capture_failure


def test_crash_capture_failure_preserves_original_failure(tmp_path: Path, monkeypatch) -> None:
    def broken(*args):
        raise OSError("unavailable")

    monkeypatch.setattr("uiautomation.utils.failure_artifacts.collect_simulator_crashes", broken)
    output = capture_failure(
        tmp_path, "test", "call", None, None, "original failure", ("id", "app", 0)
    )
    metadata = json.loads((output / "failure.json").read_text())
    assert metadata["failure"] == "original failure"
    assert "Crash reports: OSError" in metadata["capture_errors"]


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


def test_artifact_links_are_relative_and_url_encoded(tmp_path: Path) -> None:
    """Moving an extracted CI bundle preserves links, including spaces in paths."""
    destination = tmp_path / "artifacts" / "run one" / "failed"
    destination.mkdir(parents=True)
    (destination / "screen.png").touch()
    (destination / "page.xml").touch()
    report = tmp_path / "reports" / "report.html"
    assert artifact_links(destination, report) == [
        ("page.xml", "../artifacts/run%20one/failed/page.xml"),
        ("screen.png", "../artifacts/run%20one/failed/screen.png"),
    ]
