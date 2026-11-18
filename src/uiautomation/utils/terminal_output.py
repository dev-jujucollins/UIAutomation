"""Readable pytest progress: one line per test, grouped by app, in plain words.

Shown at pytest's default verbosity, replacing the rows of dots::

    Settings
      ✓ wifi toggle reflects state  2.3s
      ✗ airplane mode turns off radios  4.1s

``-v`` gives pytest's standard per-test lines with full test IDs, and ``-q`` keeps the
compact dots. In parallel runs tests finish out of order, so each line names its area
instead (``✓ Settings › wifi toggle reflects state  2.3s``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

MARKS = {
    "passed": ("✓", {"green": True}),
    "failed": ("✗", {"red": True, "bold": True}),
    "skipped": ("–", {"yellow": True}),
}
# Words that read wrong when only the first letter is capitalized.
SPELLINGS = {"wda": "WDA", "wifi": "Wi-Fi", "cli": "CLI", "html": "HTML", "xcresult": "xcresult"}


def describe(nodeid: str, path: str | None = None) -> tuple[str, str]:
    """Turn a node ID into (area, title).

    ``tests/integration/test_calendar_lifecycle.py::TestEvents::test_add_event[light]``
    becomes ``("Calendar lifecycle", "add event (light)")``. ``path`` overrides the file
    part, which pytest leaves empty for files outside the root directory.
    """
    # Parameters come last and may themselves contain "::" or brackets.
    base, _, params = nodeid.partition("[")
    node_path, *parts = base.split("::")
    path = path or node_path
    words = [SPELLINGS.get(word, word) for word in Path(path).stem.removeprefix("test_").split("_")]
    area = " ".join(words)
    area = area[:1].upper() + area[1:]
    function = parts[-1] if parts else ""
    title = function.removeprefix("test_").replace("_", " ")
    if params:
        values = [value for value in params.removesuffix("]").split("-") if value]
        title += f" ({', '.join(values)})"
    return area, title


def _shown(report: pytest.TestReport) -> bool:
    """One line per test: its call, or the setup/teardown that failed or skipped it."""
    return (
        report.when == "call"
        or (report.when == "setup" and not report.passed)
        or (report.when == "teardown" and report.failed)
    )


class ReadableOutput:
    """Registered by the plugin when pytest runs at default verbosity in a terminal process."""

    def __init__(self, config: pytest.Config) -> None:
        self.config = config
        self.area: str | None = None
        workers = config.getoption("numprocesses", default=None)
        self.parallel = bool(workers) and str(workers) != "0"

    def _reporter(self):
        return self.config.pluginmanager.get_plugin("terminalreporter")

    @pytest.hookimpl(trylast=True)
    def pytest_collection_finish(self, session: pytest.Session) -> None:
        reporter = self._reporter()
        if reporter is not None:
            # File paths would precede every group; the area headings replace them.
            reporter.showfspath = False

    @pytest.hookimpl(wrapper=True)
    def pytest_report_teststatus(self, report: pytest.TestReport, config: pytest.Config):
        category, letter, word = yield
        return category, "", word

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        reporter = self._reporter()
        if reporter is None or not _shown(report):
            return
        area, title = describe(report.nodeid, report.location[0])
        mark, style = MARKS.get(report.outcome, ("?", {}))
        if self.parallel:
            reporter.ensure_newline()
            reporter.write_line(f"{mark} {area} › {title}  {report.duration:.1f}s", **style)
            return
        if area != self.area:
            reporter.ensure_newline()
            reporter.write_line("")
            reporter.write_line(area, bold=True)
            self.area = area
        reporter.write_line(f"  {mark} {title}  {report.duration:.1f}s", **style)


def register(config: pytest.Config) -> None:
    """Use readable lines at default verbosity, never in xdist workers (they don't print)."""
    if hasattr(config, "workerinput") or config.get_verbosity() != 0:
        return
    config.pluginmanager.register(ReadableOutput(config), "uiautomation-readable-output")
