"""Turn xcodebuild's test output into one readable line per test.

xcodebuild prints the whole build (thousands of lines on a first build) before any
results, then XCTest's raw lines::

    Test Case '-[UIAutomationUITests.SettingsTests testSettingsAppLaunches]' passed (8.665 seconds).

``XcodebuildProgress`` reads that output line by line and prints::

    Settings
      ✓ settings app launches  8.7s
      – locator health  11.6s
          Diagnostics require UIAUTOMATION_RUN_DIAGNOSTICS=1

The full output still goes to ``xcodebuild.log`` in the run folder, and compiler
errors are shown in full when the build fails.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

# Classic XCTest lines, and the form Xcode uses for parallel testing on clones.
_RESULT = re.compile(
    r"^Test Case '-\[(?:[\w.]+\.)?(?P<cls>\w+) (?P<method>\w+)\]' "
    r"(?P<status>passed|failed|skipped) \((?P<seconds>[\d.]+) seconds\)"
)
_PARALLEL_RESULT = re.compile(
    r"^Test [Cc]ase '(?:[\w.]+\.)?(?P<cls>\w+)\.(?P<method>\w+)\(\)' "
    r"(?P<status>passed|failed|skipped) on '.*?' \((?P<seconds>[\d.]+) seconds\)"
)
_STARTED = re.compile(r"^Test Case '-\[(?:[\w.]+\.)?(?P<cls>\w+) (?P<method>\w+)\]' started")
# Failure and skip notes: "<file>:<line>: [error: ]-[Target.Class method] : <message>".
_NOTE = re.compile(
    r"^(?P<file>/\S+?\.swift):(?P<line>\d+): (?:error: )?"
    r"-\[(?:[\w.]+\.)?(?P<cls>\w+) (?P<method>\w+)\] : (?P<message>.*)$"
)
_BUILD_ERROR = re.compile(r"^(?P<file>/\S+?):(?P<line>\d+):(?:\d+:)? error: (?P<message>.*)$")
_TESTING = re.compile(r"^Test Suite '.+' started")

MARKS = {
    "passed": ("✓", "\033[32m"),
    "failed": ("✗", "\033[1;31m"),
    "skipped": ("–", "\033[33m"),
}
BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"


def words(identifier: str) -> str:
    """``testWiFiToggleReflectsState`` -> ``wi-fi toggle reflects state``; keeps acronyms."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", identifier)
    parts = [part if part.isupper() and len(part) > 1 else part.lower() for part in spaced.split()]
    return " ".join(parts).replace("wi fi", "wi-fi")


def app_name(cls: str) -> str:
    """``MapsNavigationTests`` -> ``Maps navigation``."""
    name = words(cls.removesuffix("Tests")) or cls
    return name[:1].upper() + name[1:]


def method_name(method: str) -> str:
    return words(method.removeprefix("test")) or method


@dataclass
class XcodebuildProgress:
    """Feed xcodebuild output lines; readable lines go to ``write``."""

    write: Callable[[str], None]
    color: bool = True
    counts: dict[str, int] = field(default_factory=lambda: {"passed": 0, "failed": 0, "skipped": 0})
    build_errors: list[str] = field(default_factory=list)
    _notes: dict[tuple[str, str], list[str]] = field(default_factory=dict)
    _area: str | None = None
    _testing: bool = False

    def _paint(self, text: str, style: str) -> str:
        return f"{style}{text}{RESET}" if self.color and style else text

    def feed(self, line: str) -> None:
        line = line.rstrip("\n")
        result = _RESULT.match(line) or _PARALLEL_RESULT.match(line)
        if result:
            self._result(result)
            return
        note = _NOTE.match(line)
        if note:
            message = note["message"]
            if message.startswith("Test skipped - "):
                text = message.removeprefix("Test skipped - ")
            else:
                text = f"{note['file'].rsplit('/', 1)[-1]}:{note['line']}  {message}"
            self._notes.setdefault((note["cls"], note["method"]), []).append(text)
            return
        if not self._testing and _TESTING.match(line):
            self._testing = True
            self.write(self._paint("Testing…", DIM))
            return
        started = _STARTED.match(line)
        if started:
            self._heading(app_name(started["cls"]))
            return
        error = _BUILD_ERROR.match(line)
        if error and not self._testing:
            self.build_errors.append(
                f"{error['file'].rsplit('/', 1)[-1]}:{error['line']}  {error['message']}"
            )

    def _heading(self, area: str) -> None:
        if area != self._area:
            self.write("")
            self.write(self._paint(area, BOLD))
            self._area = area

    def _result(self, match: re.Match[str]) -> None:
        cls, method, status = match["cls"], match["method"], match["status"]
        self._heading(app_name(cls))
        self.counts[status] += 1
        mark, style = MARKS[status]
        seconds = float(match["seconds"])
        self.write(self._paint(f"  {mark} {method_name(method)}  {seconds:.1f}s", style))
        for note in self._notes.pop((cls, method), []):
            self.write(self._paint(f"      {note}", DIM if status == "skipped" else ""))

    def summary(self) -> str:
        parts = [f"{self.counts[status]} {status}" for status in MARKS if self.counts[status]]
        return ", ".join(parts) if parts else "no tests ran"
