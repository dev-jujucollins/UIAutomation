"""xcodebuild's output becomes one readable line per test."""

import sys
from pathlib import Path

import pytest

from uiautomation.utils import swift_runner
from uiautomation.utils.xcodebuild_output import XcodebuildProgress, app_name, method_name

# Taken from a real run of SettingsTests on Xcode 27.2.
REAL_RUN = """\
CompileSwift normal arm64 /Users/julius/Dev/UIAutomation/swift/UIAutomationUITests/SettingsTests.swift
Test Suite 'Selected tests' started at 2026-11-17 16:23:38.087.
Test Suite 'UIAutomationUITests.xctest' started at 2026-11-17 16:23:38.090.
Test Suite 'SettingsTests' started at 2026-11-17 16:23:38.090.
Test Case '-[UIAutomationUITests.SettingsTests testLocatorHealth]' started.
    t =     0.00s Start Test at 2026-11-17 16:23:38.091
/Users/julius/Dev/UIAutomation/swift/UIAutomationUITests/Support/RunOptions.swift:42: -[UIAutomationUITests.SettingsTests testLocatorHealth] : Test skipped - Diagnostics require UIAUTOMATION_RUN_DIAGNOSTICS=1
Test Case '-[UIAutomationUITests.SettingsTests testLocatorHealth]' skipped (11.619 seconds).
Test Case '-[UIAutomationUITests.SettingsTests testSettingsAppLaunches]' started.
Test Case '-[UIAutomationUITests.SettingsTests testSettingsAppLaunches]' passed (8.665 seconds).
Test Suite 'SettingsTests' passed at 2026-11-17 16:23:58.376.
\t Executed 2 tests, with 1 test skipped and 0 failures (0 unexpected) in 20.284 (20.286) seconds
** TEST SUCCEEDED **
"""


def _read(text: str) -> tuple[XcodebuildProgress, list[str]]:
    lines: list[str] = []
    progress = XcodebuildProgress(lines.append, color=False)
    for line in text.splitlines():
        progress.feed(line)
    return progress, lines


def test_a_real_run_reads_as_one_line_per_test() -> None:
    progress, lines = _read(REAL_RUN)
    assert lines == [
        "Testing…",
        "",
        "Settings",
        "  – locator health  11.6s",
        "      Diagnostics require UIAUTOMATION_RUN_DIAGNOSTICS=1",
        "  ✓ settings app launches  8.7s",
    ]
    assert progress.summary() == "1 passed, 1 skipped"


def test_failures_show_where_and_why() -> None:
    _, lines = _read(
        "Test Suite 'MapsTests' started at 2026-11-17 16:23:38.090.\n"
        "Test Case '-[UIAutomationUITests.MapsTests testSearchShowsResults]' started.\n"
        "/Users/julius/Dev/UIAutomation/swift/UIAutomationUITests/MapsTests.swift:31: error: "
        "-[UIAutomationUITests.MapsTests testSearchShowsResults] : "
        "XCTAssertTrue failed - Results list did not appear\n"
        "Test Case '-[UIAutomationUITests.MapsTests testSearchShowsResults]' failed (6.020 seconds).\n"
    )
    assert lines[-2:] == [
        "  ✗ search shows results  6.0s",
        "      MapsTests.swift:31  XCTAssertTrue failed - Results list did not appear",
    ]


def test_parallel_results_are_read_too() -> None:
    progress, lines = _read(
        "Test case 'SettingsTests.testSettingsAppLaunches()' passed on "
        "'Clone 1 of iPhone 18 Pro - UIAutomationUITests-Runner (4321)' (8.665 seconds)\n"
    )
    assert lines[-1] == "  ✓ settings app launches  8.7s"
    assert progress.counts["passed"] == 1


def test_build_errors_are_kept_until_testing_starts() -> None:
    progress, lines = _read(
        "/Users/julius/Dev/UIAutomation/swift/UIAutomationUITests/MapsTests.swift:12:9: "
        "error: cannot find 'app' in scope\n"
        "** TEST FAILED **\n"
    )
    assert lines == []
    assert progress.build_errors == ["MapsTests.swift:12  cannot find 'app' in scope"]
    assert progress.summary() == "no tests ran"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (app_name("MapsNavigationTests"), "Maps navigation"),
        (app_name("SettingsTests"), "Settings"),
        (method_name("testWiFiToggleReflectsState"), "wi-fi toggle reflects state"),
        (method_name("testURLOpensInSafari"), "URL opens in safari"),
    ],
    ids=["two words", "one word", "Wi Fi", "acronym"],
)
def test_swift_names_read_as_words(raw: str, expected: str) -> None:
    assert raw == expected


def _script(tmp_path: Path, body: str) -> list[str]:
    script = tmp_path / "fake-xcodebuild.py"
    script.write_text(body)
    return [sys.executable, str(script)]


def test_execute_keeps_the_full_log_and_prints_readable_lines(tmp_path, capsys) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text(REAL_RUN)
    command = _script(tmp_path, f"print(open({str(sample)!r}).read(), end='')")
    log = tmp_path / "xcodebuild.log"
    assert swift_runner._execute(command, log) == 0
    assert log.read_text() == REAL_RUN
    out = capsys.readouterr().out
    assert "  ✓ settings app launches  8.7s" in out
    assert "CompileSwift" not in out and "1 passed, 1 skipped" in out


def test_execute_shows_build_errors_and_the_log_when_nothing_ran(tmp_path, capsys) -> None:
    command = _script(
        tmp_path,
        "import sys\n"
        "print('/x/MapsTests.swift:12:9: error: cannot find \\'app\\' in scope')\n"
        "sys.exit(65)\n",
    )
    log = tmp_path / "xcodebuild.log"
    assert swift_runner._execute(command, log) == 65
    err = capsys.readouterr().err
    assert "Build failed:" in err and "MapsTests.swift:12  cannot find 'app' in scope" in err
    assert f"Full xcodebuild output: {log}" in err


def test_verbose_prints_the_raw_output(tmp_path, capsys) -> None:
    command = _script(tmp_path, "print('CompileSwift normal arm64 Foo.swift')")
    swift_runner._execute(command, tmp_path / "xcodebuild.log", verbose=True)
    assert "CompileSwift normal arm64 Foo.swift" in capsys.readouterr().out
