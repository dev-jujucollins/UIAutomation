"""The CI summary reads pytest's JUnit files into a table and failure annotations."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "ci_report.py"
spec = importlib.util.spec_from_file_location("ci_report", SCRIPT)
assert spec is not None and spec.loader is not None
ci_report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci_report)

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="3">
  <testcase classname="tests.unit.test_wda_setup" name="test_reuse"
    file="tests/unit/test_wda_setup.py" line="11" time="0.20"/>
  <testcase classname="tests.unit.test_wda_setup" name="test_ports[8100-8101]"
    file="tests/unit/test_wda_setup.py" line="20" time="0.10">
    <failure message="AssertionError: assert 8100 == 8101&#10;more detail">tests/unit/helpers.py:4: in check
    raise
tests/unit/test_wda_setup.py:24: AssertionError</failure>
  </testcase>
  <testcase classname="tests.unit.test_settings" name="test_wifi"
    file="tests/unit/test_settings.py" line="5" time="0">
    <skipped message="needs a simulator"/>
  </testcase>
</testsuite></testsuites>
"""


def _write(tmp_path: Path, name: str = "unit.xml") -> Path:
    path = tmp_path / name
    path.write_text(JUNIT)
    return path


def test_cases_get_readable_names_outcomes_and_the_failing_line(tmp_path) -> None:
    suite = ci_report.read_suite(_write(tmp_path))
    assert suite.title == "Unit tests"
    assert [(case.name, case.outcome) for case in suite.cases] == [
        ("WDA setup › reuse", "passed"),
        ("WDA setup › ports (8100, 8101)", "failed"),
        ("Settings › wifi", "skipped"),
    ]
    failure = suite.cases[1]
    # The test's own line in the traceback, not the helper it called.
    assert (failure.file, failure.line) == ("tests/unit/test_wda_setup.py", 24)
    assert failure.message == "AssertionError: assert 8100 == 8101"


def test_annotations_escape_workflow_command_characters() -> None:
    case = ci_report.Case("A › b, c", "x.py", 3, 0.1, "failed", "50% done\nnext")
    assert ci_report.annotation(case) == (
        "::error file=x.py,line=3,title=A › b%2C c::50%25 done%0Anext"
    )


def test_summary_table_and_failures(tmp_path, capsys) -> None:
    summary = tmp_path / "summary.md"
    assert ci_report.main(["--summary", str(summary), str(_write(tmp_path))]) == 0
    text = summary.read_text()
    assert text.startswith("### ❌ 1 of 3 checks failed")
    assert "| Unit tests | 1 | 1 | 1 | 0.3s |" in text
    assert "- **WDA setup › ports (8100, 8101)** — `tests/unit/test_wda_setup.py:24`" in text
    assert capsys.readouterr().out.startswith("::error file=tests/unit/test_wda_setup.py,line=24,")


def test_missing_result_files_are_passed_over(tmp_path, capsys) -> None:
    assert ci_report.main([str(tmp_path / "simulator.xml")]) == 0
    assert "No test results" in capsys.readouterr().out
