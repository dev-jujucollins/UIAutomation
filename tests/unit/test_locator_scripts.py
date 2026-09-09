"""Unit tests for locator inspection scripts."""

from __future__ import annotations

from types import SimpleNamespace

from scripts import inspect_locators


def test_save_page_source_writes_xml(tmp_path) -> None:
    """Locator helper should persist the raw page source to disk."""
    original_output_dir = inspect_locators.OUTPUT_DIR
    inspect_locators.OUTPUT_DIR = tmp_path
    driver = SimpleNamespace(page_source="<AppiumPageSource />")

    try:
        output_path = inspect_locators.save_page_source(driver, "sample.xml")
    finally:
        inspect_locators.OUTPUT_DIR = original_output_dir

    assert tmp_path.joinpath("sample.xml").read_text(encoding="utf-8") == "<AppiumPageSource />"
    assert output_path == str(tmp_path / "sample.xml")
