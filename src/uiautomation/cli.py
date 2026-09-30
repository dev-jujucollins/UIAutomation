"""Command-line tools for the UIAutomation framework."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from uiautomation.utils.doctor import diagnose_environment, format_report
from uiautomation.utils.local_runner import SUITES, run_suite
from uiautomation.utils.run_history import format_history, summarize_history

_VALUE_OPTIONS = {
    "--device-name": "Exact simulator or physical-device name",
    "--platform-version": "Exact iOS runtime version",
    "--appium-server": "Appium server URL",
    "--udid": "Physical device identifier",
    "--team-id": "Signing team for physical-device WebDriverAgent",
    "--timeout": "Per-test timeout in seconds (pytest default: 120)",
}
_FLAG_OPTIONS = {
    "--headless-simulator": "Skip opening Device Hub",
    "--restart-simulator": "Restart the simulator during session setup",
    "--no-reset": "Preserve app/device state between sessions",
    "--skip-simulator-state-reset": "Skip session-level simulator state reset",
    "--run-integration": "Enable device tests (automatic for device presets)",
    "--run-diagnostics": "Include environment-dependent diagnostics",
    "--run-lifecycle": "Include owned-data tests on an explicitly named simulator",
    "--run-maps-navigation": "Include Maps guidance on an explicitly named simulator",
}


def _add_run_options(parser: argparse.ArgumentParser) -> None:
    """Share reporting and common pytest options across direct and legacy commands."""
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    delivery = parser.add_mutually_exclusive_group()
    delivery.add_argument("--email", action="store_true", help="Send summary and HTML report")
    delivery.add_argument(
        "--email-preview", action="store_true", help="Generate HTML and preview without sending"
    )
    parser.add_argument("--email-config", type=Path, default=Path("email.local"))
    for option, help_text in _VALUE_OPTIONS.items():
        parser.add_argument(option, help=help_text)
    for option, help_text in _FLAG_OPTIONS.items():
        parser.add_argument(option, action="store_true", help=help_text)
    parser.add_argument("-m", dest="markexpr", help="Filter tests by pytest marker expression")
    parser.add_argument("-k", dest="keyword", help="Filter tests by pytest name expression")
    parser.add_argument("-v", action="count", default=0, help="Increase pytest verbosity")
    parser.add_argument("-q", action="count", default=0, help="Reduce pytest verbosity")
    parser.add_argument(
        "pytest_args", nargs=argparse.REMAINDER, help="Other pytest options after --"
    )


def _forward_options(args: argparse.Namespace) -> list[str]:
    """Translate common options, preserving explicit pytest overrides after the separator."""
    forwarded = []
    for option in _VALUE_OPTIONS:
        value = getattr(args, option[2:].replace("-", "_"))
        if value is not None:
            forwarded.extend([option, value])
    for option in _FLAG_OPTIONS:
        if getattr(args, option[2:].replace("-", "_")):
            forwarded.append(option)
    for option, value in (("-m", args.markexpr), ("-k", args.keyword)):
        if value is not None:
            forwarded.extend([option, value])
    forwarded.extend(["-v"] * args.v)
    forwarded.extend(["-q"] * args.q)
    extra = args.pytest_args
    return forwarded + (extra[1:] if extra[:1] == ["--"] else extra)


def main(argv: list[str] | None = None) -> int:
    """Run a framework command and return its process exit code."""
    parser = argparse.ArgumentParser(prog="uiautomation", allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    descriptions = {
        "unit": "Run device-free unit tests",
        "integration": "Run regular device integration tests",
        "all": "Run unit and regular integration tests",
        "smoke": "Run quick integration checks",
        "journey": "Run navigation journeys",
    }
    for suite in SUITES:
        direct = commands.add_parser(suite, help=descriptions[suite], allow_abbrev=False)
        direct.set_defaults(suite=suite)
        _add_run_options(direct)
    run = commands.add_parser(
        "run", help="Compatibility alias: run --suite NAME", allow_abbrev=False
    )
    run.add_argument("--suite", choices=tuple(SUITES), default="unit")
    _add_run_options(run)
    history = commands.add_parser("history", help="Compare completed run manifests")
    history.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    history.add_argument("--limit", type=int, default=10)
    history.add_argument("--json", action="store_true")
    doctor = commands.add_parser("doctor", help="Check local simulator test prerequisites")
    doctor.add_argument(
        "--device-name", help="Exact simulator name (default: framework preference)"
    )
    doctor.add_argument("--platform-version", help="Exact iOS runtime version")
    doctor.add_argument("--appium-server", default="http://localhost:4723", help="Appium base URL")
    doctor.add_argument(
        "--headless-simulator", action="store_true", help="Do not require Device Hub"
    )
    doctor.add_argument(
        "--require-server", action="store_true", help="Fail when Appium is not already running"
    )
    doctor.add_argument(
        "--run-driver-doctor",
        action="store_true",
        help="Opt in to upstream Appium doctor (may apply fixes or start a tunnel; 60s limit)",
    )
    doctor.add_argument("--json", action="store_true", help="Print machine-readable results")
    args = parser.parse_args(argv)
    if args.command == "run" or args.command in SUITES:
        forwarded = _forward_options(args)
        if any(arg == "--artifacts-dir" or arg.startswith("--artifacts-dir=") for arg in forwarded):
            parser.error("Set --artifacts-dir before -- so the runner owns its report directory")
        return run_suite(
            args.suite,
            forwarded,
            args.artifacts_dir,
            args.email,
            args.email_preview,
            args.email_config,
        )
    if args.command == "history":
        if args.limit < 1:
            parser.error("--limit must be positive")
        if not args.artifacts_dir.is_dir():
            parser.error("--artifacts-dir must be an existing directory")
        history_report = summarize_history(args.artifacts_dir)
        print(
            json.dumps(history_report, indent=2)
            if args.json
            else format_history(history_report, args.limit)
        )
        return 0
    report = diagnose_environment(
        device_name=args.device_name,
        platform_version=args.platform_version,
        server_url=args.appium_server,
        headless=args.headless_simulator,
        require_server=args.require_server,
        run_driver_doctor=args.run_driver_doctor,
    )
    print(json.dumps(report.to_dict(), indent=2) if args.json else format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
