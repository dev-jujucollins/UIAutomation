"""Swift runs keep xcodebuild's exit status and report like pytest runs."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from swift_samples import SUMMARY, TESTS

from uiautomation import cli
from uiautomation.utils import swift_runner


@pytest.fixture
def swift_run(tmp_path: Path, monkeypatch):
    """A repository with a run script, a fake xcodebuild result, and no real tools."""
    (tmp_path / "swift").mkdir()
    (tmp_path / "swift" / "run-tests.sh").write_text("#!/bin/bash\n")
    monkeypatch.chdir(tmp_path)
    run = MagicMock(return_value=SimpleNamespace(returncode=65))
    monkeypatch.setattr(swift_runner.subprocess, "run", run)
    monkeypatch.setattr(swift_runner, "collect_environment", lambda _: {"commit": "abc"})
    monkeypatch.setattr(
        swift_runner, "read_test_results", lambda _, kind: SUMMARY if kind == "summary" else TESTS
    )
    monkeypatch.setattr(swift_runner, "export_failure_screenshots", lambda *_: {})
    send = MagicMock()
    monkeypatch.setattr(swift_runner, "send_summary", send)
    monkeypatch.setattr(swift_runner.EmailSettings, "load", MagicMock(return_value="settings"))
    return SimpleNamespace(root=tmp_path, run=run, send=send)


def _artifacts(root: Path) -> Path:
    (folder,) = (root / "artifacts").glob("local-*")
    return folder


def test_every_run_is_recorded_and_never_emails_by_default(swift_run) -> None:
    code = swift_runner.run_swift(["SettingsTests"], Path("artifacts"), lifecycle=True)
    # xcodebuild's own status is returned; the manifest uses pytest's "1: tests failed".
    assert code == 65
    folder = _artifacts(swift_run.root)
    (manifest_path,) = folder.glob("*/run.json")
    manifest = json.loads(manifest_path.read_text())
    assert manifest["exit_status"] == 1 and manifest["runner"] == "xcuitest"
    assert manifest["options"]["run_lifecycle"] is True
    assert "Failures (1)" in (folder / "report.html").read_text()
    assert not (folder / "email.txt").exists()
    swift_run.send.assert_not_called()
    command = swift_run.run.call_args.args[0]
    assert command[0].endswith("swift/run-tests.sh")
    assert command[1] == "--result-bundle" and command[2].endswith("results.xcresult")
    assert command[3:] == ["--lifecycle", "SettingsTests"]


def test_options_translate_to_the_run_script(swift_run) -> None:
    swift_runner.run_swift(
        [],
        Path("artifacts"),
        plan="Smoke",
        device="iPhone 18 Pro",
        os_version="27.2",
        maps_navigation=True,
        diagnostics=True,
        extra=["-test-iterations", "3"],
    )
    assert swift_run.run.call_args.args[0][3:] == [
        "--plan",
        "Smoke",
        "--device",
        "iPhone 18 Pro",
        "--os",
        "27.2",
        "--maps-navigation",
        "--diagnostics",
        "--",
        "-test-iterations",
        "3",
    ]


def test_preview_writes_the_email_without_sending(swift_run, capsys) -> None:
    assert swift_runner.run_swift([], Path("artifacts"), plan="Smoke", preview=True) == 65
    folder = _artifacts(swift_run.root)
    body = (folder / "email.txt").read_text()
    assert body.startswith("[UIAutomation] FAILED — Swift · Smoke\nExit status: 1\n")
    assert "Results: 1 passed, 1 failed, 1 skipped" in body
    assert "swift::SettingsTests/testNavigateToGeneral (call)" in body
    assert "Appium" not in body and "result bundle" in body
    assert "FAILED" in (folder / "email.html").read_text()
    assert json.loads((folder / "email-status.json").read_text()) == {"status": "preview"}
    swift_run.send.assert_not_called()
    assert "Email preview:" in capsys.readouterr().out


def test_email_sends_once_with_html_body_and_report(swift_run) -> None:
    swift_runner.run_swift([], Path("artifacts"), email=True, email_config=Path("mail.json"))
    swift_run.send.assert_called_once()
    args, kwargs = swift_run.send.call_args
    assert args[0] == "settings" and args[1] == "[UIAutomation] FAILED — Swift · All"
    assert kwargs["html_report"].startswith(b"<!doctype html>")
    assert "<style" not in kwargs["html_body"]
    folder = _artifacts(swift_run.root)
    assert json.loads((folder / "email-status.json").read_text()) == {"status": "sent"}


def test_unreadable_bundle_keeps_exit_status_and_still_reports(
    swift_run, monkeypatch, capsys
) -> None:
    def broken(*_):
        raise subprocess.CalledProcessError(1, ["xcrun"], stderr="private path")

    monkeypatch.setattr(swift_runner, "read_test_results", broken)
    assert swift_runner.run_swift([], Path("artifacts"), preview=True) == 65
    folder = _artifacts(swift_run.root)
    assert not (folder / "report.html").exists()
    body = (folder / "email.txt").read_text()
    assert "[UIAutomation] ERROR" in body and "No run manifest available" in body
    assert "HTML attachment unavailable" in body
    errors = capsys.readouterr().err
    assert "could not be recorded" in errors and "private path" not in errors


def test_delivery_failure_keeps_exit_status_without_leaking_details(swift_run, capsys) -> None:
    swift_run.send.side_effect = RuntimeError("smtp-password-123")
    assert swift_runner.run_swift([], Path("artifacts"), email=True) == 65
    folder = _artifacts(swift_run.root)
    assert json.loads((folder / "email-status.json").read_text()) == {
        "status": "failed",
        "error_type": "RuntimeError",
    }
    assert "smtp-password-123" not in capsys.readouterr().err


def test_oversized_report_is_rebuilt_without_screenshots(swift_run, monkeypatch) -> None:
    shot = swift_run.root / "shot.jpeg"
    shot.write_bytes(b"\xff\xd8" + b"0" * 60_000)
    monkeypatch.setattr(
        swift_runner,
        "export_failure_screenshots",
        lambda *_: {"SettingsTests/testNavigateToGeneral()": shot},
    )
    monkeypatch.setattr(swift_runner, "MAX_HTML_BYTES", 40_000)
    swift_runner.run_swift([], Path("artifacts"))
    assert "data:image" not in (_artifacts(swift_run.root) / "report.html").read_text()


def test_missing_run_script_fails_before_running(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert swift_runner.run_swift([], Path("artifacts")) == 127
    assert "repository root" in capsys.readouterr().err
    assert not (tmp_path / "artifacts").exists()


def test_cli_accepts_both_option_spellings_and_xcodebuild_passthrough(monkeypatch) -> None:
    run = MagicMock(return_value=0)
    monkeypatch.setattr(cli, "run_swift", run)
    assert (
        cli.main(
            [
                "swift",
                "RemindersTests",
                "--device-name",
                "iPhone 18 Pro",
                "--os",
                "27.2",
                "--run-lifecycle",
                "--diagnostics",
                "--email-preview",
                "--",
                "-test-iterations",
                "3",
            ]
        )
        == 0
    )
    args, kwargs = run.call_args
    assert args == (["RemindersTests"], Path("artifacts"))
    assert kwargs == {
        "plan": None,
        "device": "iPhone 18 Pro",
        "os_version": "27.2",
        "udid": None,
        "lifecycle": True,
        "maps_navigation": False,
        "diagnostics": True,
        "email": False,
        "preview": True,
        "email_config": Path("email.local"),
        "extra": ["-test-iterations", "3"],
    }
    with pytest.raises(SystemExit):
        cli.main(["swift", "--email", "--email-preview"])
