"""Run local pytest suites and optionally deliver a post-run summary."""

import json
import subprocess
import sys
from pathlib import Path
from time import monotonic
from uuid import uuid4

from uiautomation.utils.email_reporting import (
    EmailSettings,
    KeychainCredentialError,
    render_summary,
    send_summary,
)

SUITES = {
    "unit": ["tests/unit"],
    "integration": ["tests/integration", "--run-integration"],
    "all": ["tests", "--run-integration"],
    "smoke": ["tests/integration", "--run-integration", "-m", "smoke"],
    "journey": [
        "tests/integration",
        "--run-integration",
        "-m",
        "journey and not lifecycle and not maps_navigation",
    ],
}
MAX_HTML_BYTES = 10 * 1024 * 1024


def _report_signature(path: Path) -> tuple[int, int, int] | None:
    """Identify an existing report so failed startup cannot attach a stale file."""
    try:
        stat = path.stat()
        return stat.st_ino, stat.st_mtime_ns, stat.st_size
    except OSError:
        return None


def run_suite(
    suite: str,
    pytest_args: list[str],
    artifacts: Path,
    email: bool = False,
    preview: bool = False,
    email_config: Path = Path("email.local"),
) -> int:
    """Keep pytest's exit status even if configuration or email delivery fails."""
    root = artifacts.resolve() / f"local-{uuid4().hex}"
    root.mkdir(parents=True)
    report_path = root / "report.html"
    report_options: list[str] = []
    if email or preview:
        # Honor the last explicit pytest-html destination, otherwise own a unique report.
        for index, arg in enumerate(pytest_args):
            if arg == "--html" and index + 1 < len(pytest_args):
                report_path = Path(pytest_args[index + 1]).resolve()
            elif arg.startswith("--html="):
                report_path = Path(arg.split("=", 1)[1]).resolve()
        report_options = ["--html", str(report_path), "--self-contained-html"]
    previous_report = _report_signature(report_path)
    command = [
        sys.executable,
        "-m",
        "pytest",
        *SUITES[suite],
        *pytest_args,
        *report_options,
        "--artifacts-dir",
        str(root),
    ]
    started = monotonic()
    try:
        code = subprocess.run(command, check=False).returncode
        if code < 0:
            code = 128 - code
    except KeyboardInterrupt:
        code = 130
    except OSError:
        print("Unable to start pytest.", file=sys.stderr)
        code = 127
    elapsed = monotonic() - started
    print(f"Run artifacts: {root}")
    if not email and not preview:
        return code
    delivery = {"status": "preview" if preview else "failed"}
    try:
        manifest = None
        for path in root.glob("*/run.json"):
            try:
                candidate = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(candidate, dict) and candidate.get("worker") is None:
                    manifest = candidate
                    break
            except (OSError, ValueError):
                continue
        subject, body = render_summary(suite, code, elapsed, manifest)
        html_report = None
        if _report_signature(report_path) != previous_report:
            try:
                with report_path.open("rb") as report:
                    content = report.read(MAX_HTML_BYTES + 1)
                if content and len(content) <= MAX_HTML_BYTES:
                    html_report = content
            except OSError:
                pass
        body += f"Local run artifacts: {root}\n"
        if html_report is not None:
            body += f"HTML report attached as report.html. Local report: {report_path}\n"
            body += "Failure evidence links require the local artifact folder.\n"
        else:
            body += "HTML attachment unavailable (not generated, unreadable, or over 10 MB).\n"
            print(
                "HTML report unavailable; email summary will have no attachment.", file=sys.stderr
            )
        (root / "email.txt").write_text(body, encoding="utf-8")
        if email:
            send_summary(EmailSettings.load(email_config), subject, body, html_report=html_report)
            delivery["status"] = "sent"
            print("Email summary sent.")
        else:
            print(f"Email preview: {root / 'email.txt'}")
    except Exception as error:
        # Exception messages can contain provider credentials or account data.
        delivery = {"status": "failed", "error_type": type(error).__name__}
        hint = (
            str(error)
            if isinstance(error, KeychainCredentialError)
            else "Check email settings, Keychain, and SMTP access."
        )
        print(
            f"Email reporting failed ({type(error).__name__}); pytest exit status preserved. {hint}",
            file=sys.stderr,
        )
    try:
        (root / "email-status.json").write_text(json.dumps(delivery, indent=2), encoding="utf-8")
    except OSError:
        print(
            "Unable to save email delivery status; pytest exit status preserved.", file=sys.stderr
        )
    return code
