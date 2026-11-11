"""The Swift HTML report is self-contained, failure-first, and safe to email."""

from swift_samples import SUMMARY, TESTS

from uiautomation.utils.swift_report import (
    MAX_EMBEDDED_SCREENSHOT_BYTES,
    format_duration,
    render_email_html,
    render_report,
)
from uiautomation.utils.xcresult import build_manifest, flatten_tests

TESTS_LIST = flatten_tests(TESTS)
MANIFEST = build_manifest(
    SUMMARY,
    TESTS_LIST,
    run_id="run-1",
    exit_status=1,
    options={"run_lifecycle": True, "run_diagnostics": False},
    environment={"commit": "0123456789abcdef", "working_tree_dirty": True},
)
FAILED_ID = "SettingsTests/testNavigateToGeneral()"


def test_report_leads_with_failures_and_escapes_test_output() -> None:
    html = render_report(MANIFEST, TESTS_LIST, "Swift · All", result_bundle="/tmp/r.xcresult")
    assert '<span class="pill failed">failed</span>' in html
    assert html.index("Failures (1)") < html.index("Results by app") < html.index("Skipped (1)")
    # A failure message is test output, not markup.
    assert "&lt;b&gt;General&lt;/b&gt; missing" in html and "<b>General</b>" not in html
    assert "SettingsTests.swift:30" in html
    assert "iPhone 18 Pro · iOS 27.2" in html
    assert "Opt-ins: lifecycle" in html
    assert "Commit 0123456789 (uncommitted changes)" in html
    # The skip reason drops XCTest's boilerplate prefix.
    assert "Owned-data tests require UIAUTOMATION_RUN_LIFECYCLE=1" in html
    assert "Test skipped - " not in html
    # An app whose tests were all skipped gets no empty results card.
    assert "<h3>Contacts</h3>" not in html and "<h3>Settings</h3>" in html
    assert "/tmp/r.xcresult" in html
    # One file, nothing fetched: no scripts, stylesheets or remote images.
    assert "<script" not in html and "http://" not in html and "https://" not in html


def test_screenshots_are_embedded_up_to_the_size_cap() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    html = render_report(MANIFEST, TESTS_LIST, "Swift", {FAILED_ID: png})
    assert 'src="data:image/png;base64,' in html
    jpeg = render_report(MANIFEST, TESTS_LIST, "Swift", {FAILED_ID: b"\xff\xd8jpeg"})
    assert 'src="data:image/jpeg;base64,' in jpeg
    huge = render_report(
        MANIFEST, TESTS_LIST, "Swift", {FAILED_ID: b"0" * (MAX_EMBEDDED_SCREENSHOT_BYTES + 1)}
    )
    assert "data:image" not in huge and "too large to embed" in huge


def test_a_run_with_no_tests_reads_as_failed_not_passed() -> None:
    empty = build_manifest({}, [], run_id="run-2", exit_status=65, options={}, environment={})
    html = render_report(empty, [], "Swift · Smoke")
    assert "No tests ran" in html and '<span class="pill failed">' in html
    assert "FAILED" in render_email_html(empty, [], "Swift · Smoke")


def test_passing_run_reads_as_passed() -> None:
    passed = [test for test in TESTS_LIST if test.outcome == "passed"]
    manifest = build_manifest(
        SUMMARY, passed, run_id="run-3", exit_status=0, options={}, environment={}
    )
    html = render_report(manifest, passed, "Swift")
    assert '<span class="pill passed">passed</span>' in html and "Failures" not in html
    assert "PASSED" in render_email_html(manifest, passed, "Swift")


def test_email_body_uses_inline_styles_and_lists_failures() -> None:
    html = render_email_html(MANIFEST, TESTS_LIST, "Swift · All")
    assert "<style" not in html and "<script" not in html
    assert "FAILED" in html and "<strong>1</strong> failed" in html
    assert "Settings › testNavigateToGeneral" in html
    assert "&lt;b&gt;General&lt;/b&gt;" in html


def test_durations_read_naturally() -> None:
    assert format_duration(8.24) == "8.2s"
    assert format_duration(185.4) == "3m 05s"
