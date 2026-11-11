"""Run the Swift (XCUITest) suite, record it like a pytest run, and optionally email it."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import uuid4

from uiautomation.utils.email_reporting import (
    EmailSettings,
    KeychainCredentialError,
    render_summary,
    send_summary,
)
from uiautomation.utils.run_reporting import working_tree_dirty
from uiautomation.utils.swift_report import render_email_html, render_report
from uiautomation.utils.xcresult import (
    SwiftTest,
    build_manifest,
    export_failure_screenshots,
    flatten_tests,
    read_test_results,
)

RUN_SCRIPT = Path("swift") / "run-tests.sh"
MAX_HTML_BYTES = 10 * 1024 * 1024
SWIFT_EVIDENCE = (
    "Screen recordings, step logs, and accessibility hierarchies remain in the result "
    "bundle on the Mac."
)


def _probe(command: list[str], cwd: Path) -> str | None:
    """Read a bounded version probe; a missing tool is reported as unavailable."""
    try:
        result = subprocess.run(  # noqa: S603
            command, cwd=cwd, capture_output=True, text=True, check=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def collect_environment(repository: Path) -> dict[str, Any]:
    """Capture the commit and tool versions behind a Swift run."""
    return {
        "commit": _probe(["git", "rev-parse", "HEAD"], repository),
        "working_tree_dirty": working_tree_dirty(repository),
        "python": platform.python_version(),
        "host_platform": platform.system(),
        "tools": {"xcode": _probe(["xcodebuild", "-version"], repository)},
    }


def run_label(plan: str | None, tests: list[str]) -> str:
    """Name a run for subjects and report headers, e.g. ``Swift · Smoke``."""
    if tests:
        shown = ", ".join(tests[:3]) + (f" +{len(tests) - 3} more" if len(tests) > 3 else "")
        return f"Swift · {shown}"
    return f"Swift · {plan or 'All'}"


def _command(
    script: Path,
    bundle: Path,
    tests: list[str],
    *,
    plan: str | None,
    device: str | None,
    os_version: str | None,
    udid: str | None,
    lifecycle: bool,
    maps_navigation: bool,
    diagnostics: bool,
    extra: list[str],
) -> list[str]:
    """Translate the run's options into ``run-tests.sh`` arguments."""
    command = [str(script), "--result-bundle", str(bundle)]
    for option, value in (
        ("--plan", plan),
        ("--device", device),
        ("--os", os_version),
        ("--udid", udid),
    ):
        if value is not None:
            command += [option, value]
    for option, enabled in (
        ("--lifecycle", lifecycle),
        ("--maps-navigation", maps_navigation),
        ("--diagnostics", diagnostics),
    ):
        if enabled:
            command.append(option)
    command += tests
    if extra:
        command += ["--", *extra]
    return command


def _load_screenshots(bundle: Path, folder: Path, tests: list[SwiftTest]) -> dict[str, bytes]:
    """Read failure screenshots; a report without pictures beats no report."""
    if not any(test.outcome == "failed" for test in tests):
        return {}
    try:
        return {
            identifier: path.read_bytes()
            for identifier, path in export_failure_screenshots(bundle, folder).items()
        }
    except (OSError, ValueError, subprocess.SubprocessError):
        print("Failure screenshots could not be exported; report has none.", file=sys.stderr)
        return {}


def run_swift(
    tests: list[str],
    artifacts: Path,
    *,
    plan: str | None = None,
    device: str | None = None,
    os_version: str | None = None,
    udid: str | None = None,
    lifecycle: bool = False,
    maps_navigation: bool = False,
    diagnostics: bool = False,
    email: bool = False,
    preview: bool = False,
    email_config: Path = Path("email.local"),
    extra: list[str] | None = None,
) -> int:
    """Run Swift tests and keep xcodebuild's exit status whatever reporting does.

    Every run leaves ``run.json`` and ``report.html`` beside its result bundle, so
    ``uiautomation history`` covers Swift runs. Email is opt-in, as for pytest runs.

    Args:
        tests: Test classes or ``Class/testMethod`` names; empty runs the plan.
        artifacts: Root directory for run artifacts.
        plan: Test plan name (``All``, ``Smoke``, ``Journey``).
        device: Simulator name.
        os_version: iOS version of the simulator.
        udid: Exact simulator, instead of ``device`` and ``os_version``.
        lifecycle: Enable tests that save and delete their own data.
        maps_navigation: Enable the Maps guidance test.
        diagnostics: Enable locator-health and accessibility diagnostics.
        email: Send the summary and report.
        preview: Write the summary and report without sending.
        email_config: Nonsecret SMTP settings file.
        extra: Arguments passed to xcodebuild unchanged.
    """
    repository = Path.cwd()
    script = repository / RUN_SCRIPT
    if not script.is_file():
        print(f"{RUN_SCRIPT} not found; run this from the repository root.", file=sys.stderr)
        return 127
    run_id = uuid4().hex
    root = artifacts.resolve() / f"local-{uuid4().hex}"
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    bundle = run_dir / "results.xcresult"
    command = _command(
        script,
        bundle,
        tests,
        plan=plan,
        device=device,
        os_version=os_version,
        udid=udid,
        lifecycle=lifecycle,
        maps_navigation=maps_navigation,
        diagnostics=diagnostics,
        extra=extra or [],
    )
    started = monotonic()
    try:
        code = subprocess.run(command, check=False).returncode  # noqa: S603
        if code < 0:
            code = 128 - code
    except KeyboardInterrupt:
        code = 130
    except OSError:
        print("Unable to start the Swift test run.", file=sys.stderr)
        code = 127
    elapsed = monotonic() - started
    print(f"Run artifacts: {root}")

    label = run_label(plan, tests)
    manifest: dict[str, Any] | None = None
    results: list[SwiftTest] = []
    report: bytes | None = None
    try:
        results = flatten_tests(read_test_results(bundle, "tests"))
        failed = any(test.outcome == "failed" for test in results)
        manifest = build_manifest(
            read_test_results(bundle, "summary"),
            results,
            run_id=run_id,
            # Recorded with pytest's meanings (1: tests failed) so both runners read alike.
            exit_status=1 if failed else code,
            options={
                "run_lifecycle": lifecycle,
                "run_maps_navigation": maps_navigation,
                "run_diagnostics": diagnostics,
                "plan": plan,
            },
            environment=collect_environment(repository),
        )
        (run_dir / "run.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        screenshots = _load_screenshots(bundle, run_dir / "screenshots", results)
        report = render_report(manifest, results, label, screenshots, str(bundle)).encode()
        if len(report) > MAX_HTML_BYTES:
            # Still too big for email with every screenshot at its cap: drop the pictures.
            report = render_report(manifest, results, label, None, str(bundle)).encode()
        (root / "report.html").write_bytes(report)
        print(f"HTML report: {root / 'report.html'}")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(
            f"Swift run could not be recorded ({type(error).__name__}); "
            "xcodebuild exit status preserved.",
            file=sys.stderr,
        )
    if not email and not preview:
        return code

    delivery = {"status": "preview" if preview else "failed"}
    try:
        status = manifest["exit_status"] if manifest is not None else code
        subject, body = render_summary(
            label, status, elapsed, manifest, exit_label="Exit status", evidence=SWIFT_EVIDENCE
        )
        body += f"Local run artifacts: {root}\n"
        if report is not None:
            body += f"HTML report attached as report.html. Local report: {root / 'report.html'}\n"
        else:
            body += "HTML attachment unavailable (the run could not be read).\n"
        html_body = render_email_html(manifest, results, label) if manifest is not None else None
        (root / "email.txt").write_text(body, encoding="utf-8")
        if html_body is not None:
            (root / "email.html").write_text(html_body, encoding="utf-8")
        if email:
            send_summary(
                EmailSettings.load(email_config),
                subject,
                body,
                html_report=report,
                html_body=html_body,
            )
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
            f"Email reporting failed ({type(error).__name__}); "
            f"xcodebuild exit status preserved. {hint}",
            file=sys.stderr,
        )
    try:
        (root / "email-status.json").write_text(json.dumps(delivery, indent=2), encoding="utf-8")
    except OSError:
        print("Unable to save email delivery status.", file=sys.stderr)
    return code
