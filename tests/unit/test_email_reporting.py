"""Email transport stays encrypted and summaries omit sensitive test details."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from uiautomation.utils import email_reporting
from uiautomation.utils.email_reporting import EmailSettings, render_summary, send_summary


@pytest.mark.parametrize("returncode", [44, 36])
def test_keychain_failure_is_actionable_and_never_connects(monkeypatch, returncode) -> None:
    credentials = MagicMock(
        side_effect=subprocess.CalledProcessError(
            returncode, ["security"], output="secret-password", stderr="private-account"
        )
    )
    monkeypatch.setattr(email_reporting.subprocess, "run", credentials)
    smtp = MagicMock()
    monkeypatch.setattr(email_reporting.smtplib, "SMTP", smtp)
    with pytest.raises(email_reporting.KeychainCredentialError) as failure:
        send_summary(
            EmailSettings("host", 587, "starttls", "user", "a@example.com", "b@example.com"),
            "test",
            "body",
        )
    message = str(failure.value)
    assert ("not found" if returncode == 44 else "inaccessible") in message
    assert "uiautomation.smtp" in message
    assert "secret-password" not in message and "private-account" not in message
    smtp.assert_not_called()


@pytest.mark.parametrize("security", ["ssl", "starttls"])
def test_transport_uses_keychain_and_tls(monkeypatch, tmp_path, security: str) -> None:
    credentials = MagicMock(return_value=SimpleNamespace(stdout="secret-password\n"))
    monkeypatch.setattr(email_reporting.subprocess, "run", credentials)
    smtp = MagicMock()
    constructor = MagicMock()
    constructor.return_value.__enter__.return_value = smtp
    monkeypatch.setattr(
        email_reporting.smtplib, "SMTP_SSL" if security == "ssl" else "SMTP", constructor
    )
    settings = EmailSettings(
        "smtp.example.com",
        465 if security == "ssl" else 587,
        security,
        "user",
        "sender@example.com",
        "recipient@example.com",
    )
    send_summary(settings, "Summary", "Tests passed", html_report=b"<html>Tests passed</html>")
    assert credentials.call_args.args[0] == [
        "security",
        "find-generic-password",
        "-s",
        "uiautomation.smtp",
        "-a",
        "user",
        "-w",
    ]
    smtp.login.assert_called_once_with("user", "secret-password")
    if security == "starttls":
        assert [call[0] for call in smtp.mock_calls][:4] == ["ehlo", "starttls", "ehlo", "login"]
    else:
        assert constructor.call_args.kwargs["context"].check_hostname
    message = smtp.send_message.call_args.args[0]
    assert message["To"] == "recipient@example.com"
    assert "secret-password" not in message.as_string()
    attachments = list(message.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_content_type() == "text/html"
    assert attachments[0].get_filename() == "report.html"
    assert attachments[0].get_payload(decode=True) == b"<html>Tests passed</html>"


def test_tls_failure_never_sends_credentials(monkeypatch) -> None:
    monkeypatch.setattr(
        email_reporting.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="password")
    )
    smtp = MagicMock()
    smtp.starttls.side_effect = RuntimeError("TLS unavailable")
    connection = MagicMock()
    connection.__enter__.return_value = smtp
    monkeypatch.setattr(email_reporting.smtplib, "SMTP", lambda *a, **k: connection)
    with pytest.raises(RuntimeError):
        send_summary(
            EmailSettings("host", 587, "starttls", "user", "a@example.com", "b@example.com"),
            "test",
            "body",
        )
    smtp.login.assert_not_called()
    smtp.send_message.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("security", "plain"),
        ("port", 0),
        ("host", ""),
        ("recipient", "a@example.com\nBcc: b@example.com"),
        ("sender", "a@example.com,b@example.com"),
    ],
)
def test_invalid_settings_rejected(tmp_path: Path, field, value) -> None:
    data = {
        "host": "smtp.example.com",
        "port": 587,
        "security": "starttls",
        "username": "user",
        "sender": "a@example.com",
        "recipient": "b@example.com",
    }
    data[field] = value
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        EmailSettings.load(path)


def test_summary_omits_parameters_logs_and_reports_teardown_failure() -> None:
    subject, body = render_summary(
        "smoke",
        1,
        10,
        {
            "run_id": "run",
            "summary": {"failed": 1},
            "target": {},
            "environment": {"commit": "abc", "working_tree_dirty": True},
            "results": [
                {
                    "nodeid": "test_case[secret-token]",
                    "phase": "teardown",
                    "outcome": "failed",
                    "traceback": "private",
                }
            ],
        },
    )
    assert "FAILED" in subject
    assert "test_case (teardown)" in body
    assert "1 failed" in body
    assert "secret-token" not in body and "private" not in body


def test_missing_manifest_does_not_invent_test_counts() -> None:
    subject, body = render_summary("unit", 4, 1, None)
    assert "USAGE ERROR" in subject
    assert "No run manifest" in body
    assert "0 passed" not in body
