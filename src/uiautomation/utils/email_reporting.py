"""Opt-in SMTP summaries; passwords are read from macOS Keychain only."""

import json
import smtplib
import ssl
import subprocess
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Any


class KeychainCredentialError(RuntimeError):
    """Safe diagnostic for an SMTP credential lookup failure."""

    def __init__(self, missing: bool = False) -> None:
        message = (
            "SMTP credential not found. In Keychain Access, create a generic password "
            "named uiautomation.smtp with Account exactly matching username in email.local."
            if missing
            else "SMTP credential inaccessible. Unlock your login keychain and allow "
            "the security command to access the uiautomation.smtp password."
        )
        super().__init__(message)


@dataclass(frozen=True)
class EmailSettings:
    """Nonsecret SMTP settings; authentication uses a Keychain generic password."""

    host: str
    port: int
    security: str
    username: str
    sender: str
    recipient: str

    @classmethod
    def load(cls, path: Path) -> "EmailSettings":
        """Validate settings before reading credentials or connecting."""
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Email settings must be a JSON object")
        for field in ("host", "security", "username", "sender", "recipient"):
            if (
                not isinstance(data.get(field), str)
                or not data[field].strip()
                or any(char in data[field] for char in "\r\n")
            ):
                raise ValueError(f"Email setting {field} is missing or invalid")
        if data["security"] not in {"ssl", "starttls"}:
            raise ValueError("Email security must be ssl or starttls")
        port = data.get("port")
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Email port must be between 1 and 65535")
        for field in ("sender", "recipient"):
            address = data[field]
            if address.count("@") != 1 or any(char in address for char in " ,;<>\t"):
                raise ValueError(f"Email {field} must be one plain email address")
            if not all(address.split("@")):
                raise ValueError(f"Email {field} is invalid")
        return cls(**{key: data[key] for key in cls.__dataclass_fields__})


def send_summary(
    settings: EmailSettings, subject: str, body: str, html_report: bytes | None = None
) -> None:
    """Send a TLS-protected summary and optional HTML attachment without retries."""
    try:
        credential = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                "uiautomation.smtp",
                "-a",
                settings.username,
                "-w",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        ).stdout.rstrip("\r\n")
    except subprocess.CalledProcessError as error:
        raise KeychainCredentialError(missing=error.returncode == 44) from None
    except (subprocess.TimeoutExpired, OSError):
        raise KeychainCredentialError() from None
    if not credential:
        raise ValueError("SMTP password missing from Keychain")
    message = EmailMessage()
    message["From"] = settings.sender
    message["To"] = settings.recipient
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    message.set_content(body)
    if html_report is not None:
        message.add_attachment(html_report, maintype="text", subtype="html", filename="report.html")
    context = ssl.create_default_context()
    if settings.security == "ssl":
        connection = smtplib.SMTP_SSL(settings.host, settings.port, timeout=20, context=context)
    else:
        connection = smtplib.SMTP(settings.host, settings.port, timeout=20)
    with connection as smtp:
        if settings.security == "starttls":
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(settings.username, credential)
        smtp.send_message(message, from_addr=settings.sender, to_addrs=[settings.recipient])


def render_summary(
    suite: str, exit_code: int, elapsed: float, manifest: dict[str, Any] | None
) -> tuple[str, str]:
    """Build a concise message without logs, credentials, or parameter values."""
    status = {
        0: "PASSED",
        1: "FAILED",
        2: "INTERRUPTED",
        3: "INTERNAL ERROR",
        4: "USAGE ERROR",
        5: "NO TESTS",
        130: "INTERRUPTED",
    }.get(exit_code, "ERROR")
    subject = f"[UIAutomation] {status} — {suite}"
    lines = [subject, f"Pytest exit status: {exit_code}", f"Elapsed: {elapsed:.1f}s"]
    if manifest is None:
        lines.append("No run manifest available. Test startup or collection may have failed.")
    else:
        lines.append(f"Run: {manifest.get('run_id', 'unknown')}")
        summary = manifest.get("summary", {})
        if summary:
            lines.append(
                "Results: "
                + ", ".join(
                    f"{summary.get(key, 0)} {key}" for key in ("passed", "failed", "skipped")
                )
            )
        else:
            lines.append("Run incomplete; final result counts unavailable.")
        target = manifest.get("target", {})
        lines.append(
            f"Target: {target.get('device_name') or 'not selected'} / {target.get('platform_version') or 'not selected'}"
        )
        environment = manifest.get("environment", {})
        lines.append(
            f"Commit: {environment.get('commit') or 'unknown'}; checkout dirty: {environment.get('working_tree_dirty', 'unknown')}"
        )
        failures = sorted(
            {
                f"{result['nodeid'].split('[', 1)[0]} ({result['phase']})"
                for result in manifest.get("results", [])
                if result.get("outcome") == "failed"
            }
        )
        if failures:
            lines.extend(["Failed tests:", *failures[:20]])
            if len(failures) > 20:
                lines.append(f"... {len(failures) - 20} additional failures; see local report.")
    lines.append("Screenshots, page XML, crash reports, and Appium logs remain on the Mac.")
    return subject, "\n".join(lines) + "\n"
