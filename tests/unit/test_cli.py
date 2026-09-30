"""Direct suite commands share selection and reporting with legacy invocation."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from uiautomation import cli


@pytest.mark.parametrize("suite", ["unit", "integration", "all", "smoke", "journey"])
def test_direct_and_legacy_commands_have_identical_behavior(monkeypatch, suite):
    runner = MagicMock(return_value=1)
    monkeypatch.setattr(cli, "run_suite", runner)
    options = ["--email", "--device-name", "Test Simulator", "--platform-version", "27.0"]
    assert cli.main([suite, *options]) == 1
    direct = runner.call_args
    assert cli.main(["run", "--suite", suite, *options]) == 1
    assert runner.call_args == direct
    assert direct.args[0] == suite
    assert direct.args[1] == ["--device-name", "Test Simulator", "--platform-version", "27.0"]
    assert direct.args[3] is True


def test_common_options_forward_without_separator(monkeypatch):
    runner = MagicMock(return_value=0)
    monkeypatch.setattr(cli, "run_suite", runner)
    options = [
        "--timeout",
        "600",
        "--appium-server",
        "http://localhost:4723",
        "--udid",
        "physical-device",
        "--team-id",
        "team",
        "--headless-simulator",
        "--restart-simulator",
        "--no-reset",
        "--skip-simulator-state-reset",
        "--run-diagnostics",
        "--run-lifecycle",
        "--run-maps-navigation",
        "-m",
        "maps and journey",
        "-k",
        "round_trip",
        "-vv",
    ]
    assert cli.main(["integration", *options]) == 0
    forwarded = runner.call_args.args[1]
    for option in ("--timeout", "--appium-server", "--udid", "--team-id", "-m", "-k"):
        assert forwarded[forwarded.index(option) + 1] == options[options.index(option) + 1]
    for option in cli._FLAG_OPTIONS:
        assert (option in forwarded) == (option in options)
    assert forwarded.count("-v") == 2
    assert runner.call_args.args[3] is False


def test_pytest_passthrough_preserves_order_and_later_overrides(monkeypatch):
    runner = MagicMock(return_value=0)
    monkeypatch.setattr(cli, "run_suite", runner)
    extras = ["--timeout=600", "--maxfail=1", "-n", "0", "-o", "log_cli=true"]
    assert cli.main(["all", "--timeout", "300", "--", *extras]) == 0
    assert runner.call_args.args[1] == ["--timeout", "300", *extras]


def test_preview_and_reporting_paths_remain_runner_options(monkeypatch):
    runner = MagicMock(return_value=0)
    monkeypatch.setattr(cli, "run_suite", runner)
    assert (
        cli.main(
            [
                "unit",
                "--email-preview",
                "--artifacts-dir",
                "custom-artifacts",
                "--email-config",
                "custom.local",
                "-q",
            ]
        )
        == 0
    )
    assert runner.call_args.args == (
        "unit",
        ["-q"],
        Path("custom-artifacts"),
        False,
        True,
        Path("custom.local"),
    )


@pytest.mark.parametrize(
    "options",
    [
        ["--email", "--email-preview"],
        ["--device-nam", "Test Simulator"],
        ["--device-name"],
        ["--", "--artifacts-dir=other"],
    ],
)
def test_invalid_options_fail_before_starting_tests(monkeypatch, options):
    runner = MagicMock()
    monkeypatch.setattr(cli, "run_suite", runner)
    with pytest.raises(SystemExit) as error:
        cli.main(["smoke", *options])
    assert error.value.code == 2
    runner.assert_not_called()
