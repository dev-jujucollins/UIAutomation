"""Local email reporting never changes pytest results or sends by default."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from uiautomation.cli import main
from uiautomation.utils import local_runner


def fake_pytest(command, **kwargs):
    root = Path(command[command.index("--artifacts-dir") + 1])
    manifest = root / "current"
    manifest.mkdir()
    (manifest / "run.json").write_text(
        json.dumps({"run_id": "current", "worker": None, "summary": {"failed": 1}, "results": []})
    )
    if "--html" in command:
        Path(command[command.index("--html") + 1]).write_text("<html>Current report</html>")
    return SimpleNamespace(returncode=1)


def test_default_run_never_loads_credentials_or_sends(tmp_path: Path, monkeypatch) -> None:
    run = MagicMock(side_effect=fake_pytest)
    send = MagicMock()
    settings = MagicMock(side_effect=AssertionError("configuration must not be accessed"))
    monkeypatch.setattr(local_runner.subprocess, "run", run)
    monkeypatch.setattr(local_runner, "send_summary", send)
    monkeypatch.setattr(local_runner.EmailSettings, "load", settings)
    assert (
        main(
            [
                "run",
                "--suite",
                "smoke",
                "--artifacts-dir",
                str(tmp_path),
                "--",
                "--device-name",
                "Test Phone",
            ]
        )
        == 1
    )
    command = run.call_args.args[0]
    assert "--run-integration" in command and "Test Phone" in command
    assert "--html" not in command
    send.assert_not_called()
    settings.assert_not_called()


@pytest.mark.parametrize("code", [0, 1, 4, 5])
def test_delivery_errors_preserve_exit_code_without_secret_output(
    tmp_path: Path, monkeypatch, capsys, code
) -> None:
    monkeypatch.setattr(
        local_runner.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=code)
    )
    monkeypatch.setattr(local_runner.EmailSettings, "load", lambda _: object())
    monkeypatch.setattr(
        local_runner, "send_summary", MagicMock(side_effect=RuntimeError("secret-password"))
    )
    assert local_runner.run_suite("unit", [], tmp_path, email=True) == code
    status = json.loads(next(tmp_path.glob("*/email-status.json")).read_text())
    assert status == {"status": "failed", "error_type": "RuntimeError"}
    captured = capsys.readouterr()
    assert "secret-password" not in captured.err + captured.out


def test_preview_uses_current_report_and_never_sends(tmp_path: Path, monkeypatch) -> None:
    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "run.json").write_text('{"run_id":"stale"}')
    monkeypatch.setattr(local_runner.subprocess, "run", fake_pytest)
    send = MagicMock()
    monkeypatch.setattr(local_runner, "send_summary", send)
    assert local_runner.run_suite("unit", [], tmp_path, preview=True) == 1
    body = next(tmp_path.glob("*/email.txt")).read_text()
    assert "Run: current" in body and "stale" not in body
    assert "HTML report attached" in body
    assert next(tmp_path.glob("*/report.html")).read_text() == "<html>Current report</html>"
    send.assert_not_called()


def test_keychain_hint_reaches_cli_without_changing_result(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(local_runner.subprocess, "run", fake_pytest)
    monkeypatch.setattr(local_runner.EmailSettings, "load", lambda _: object())
    monkeypatch.setattr(
        local_runner,
        "send_summary",
        MagicMock(side_effect=local_runner.KeychainCredentialError(missing=True)),
    )
    assert local_runner.run_suite("unit", [], tmp_path, email=True) == 1
    assert "Account exactly matching username" in capsys.readouterr().err


def test_successful_opt_in_sends_once(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(local_runner.subprocess, "run", fake_pytest)
    settings = object()
    monkeypatch.setattr(local_runner.EmailSettings, "load", lambda _: settings)
    send = MagicMock()
    monkeypatch.setattr(local_runner, "send_summary", send)
    assert local_runner.run_suite("smoke", [], tmp_path, email=True) == 1
    send.assert_called_once()
    assert send.call_args.args[0] is settings
    assert send.call_args.kwargs["html_report"] == b"<html>Current report</html>"
    assert json.loads(next(tmp_path.glob("*/email-status.json")).read_text())["status"] == "sent"


@pytest.mark.parametrize("suite,path", [("integration", "tests/integration"), ("all", "tests")])
def test_full_suite_cli_emails_report_without_marker_filter(tmp_path, monkeypatch, suite, path):
    run = MagicMock(side_effect=fake_pytest)
    monkeypatch.setattr(local_runner.subprocess, "run", run)
    monkeypatch.setattr(local_runner.EmailSettings, "load", lambda _: object())
    send = MagicMock()
    monkeypatch.setattr(local_runner, "send_summary", send)
    assert (
        main(
            [
                "run",
                "--suite",
                suite,
                "--email",
                "--artifacts-dir",
                str(tmp_path),
                "--",
                "--run-lifecycle",
                "--run-maps-navigation",
                "--run-diagnostics",
                "--device-name",
                "Test Simulator",
                "--platform-version",
                "27.0",
            ]
        )
        == 1
    )
    command = run.call_args.args[0]
    assert command[3:5] == [path, "--run-integration"]
    assert "-m" not in command[3:]
    assert "--run-lifecycle" in command and "Test Simulator" in command
    assert "--run-maps-navigation" in command and "--run-diagnostics" in command
    send.assert_called_once()
    assert suite in send.call_args.args[1]
    assert send.call_args.kwargs["html_report"] == b"<html>Current report</html>"


def test_custom_html_destination_is_generated_and_attached(tmp_path, monkeypatch):
    report_path = tmp_path / "custom.html"
    run = MagicMock(side_effect=fake_pytest)
    monkeypatch.setattr(local_runner.subprocess, "run", run)
    monkeypatch.setattr(local_runner.EmailSettings, "load", lambda _: object())
    send = MagicMock()
    monkeypatch.setattr(local_runner, "send_summary", send)
    assert local_runner.run_suite("unit", [f"--html={report_path}"], tmp_path, email=True) == 1
    assert "--self-contained-html" in run.call_args.args[0]
    assert report_path.read_text() == "<html>Current report</html>"
    assert send.call_args.kwargs["html_report"] == report_path.read_bytes()


@pytest.mark.parametrize("report_kind", ["missing", "stale", "oversized"])
def test_unavailable_report_sends_summary_without_stale_attachment(
    tmp_path, monkeypatch, report_kind
):
    report_path = tmp_path / "custom.html"
    if report_kind == "stale":
        report_path.write_text("old report")

    def run(*args, **kwargs):
        if report_kind == "oversized":
            report_path.write_bytes(b"x" * (local_runner.MAX_HTML_BYTES + 1))
        return SimpleNamespace(returncode=4)

    monkeypatch.setattr(local_runner.subprocess, "run", run)
    monkeypatch.setattr(local_runner.EmailSettings, "load", lambda _: object())
    send = MagicMock()
    monkeypatch.setattr(local_runner, "send_summary", send)
    assert local_runner.run_suite("unit", ["--html", str(report_path)], tmp_path, email=True) == 4
    assert send.call_args.kwargs["html_report"] is None
    assert "HTML attachment unavailable" in send.call_args.args[2]
    assert "old report" not in send.call_args.args[2]
