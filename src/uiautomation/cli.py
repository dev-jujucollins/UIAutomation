"""Command-line tools for the UIAutomation framework."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from uiautomation.utils.doctor import diagnose_environment, format_report
from uiautomation.utils.local_runner import SUITES, run_suite
from uiautomation.utils.run_history import (
    failed_tests,
    flaky_tests,
    format_history,
    latest_run,
    rerun_options,
    summarize_history,
)
from uiautomation.utils.simulator_control import (
    SimulatorDevice,
    list_available_simulators,
    select_simulator,
    version_key,
)

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
    parser.add_argument(
        "-n",
        dest="workers",
        help="Parallel workers; each simulator worker gets its own simulator and ports",
    )
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
    for option, value in (("-n", args.workers), ("-m", args.markexpr), ("-k", args.keyword)):
        if value is not None:
            forwarded.extend([option, value])
    forwarded.extend(["-v"] * args.v)
    forwarded.extend(["-q"] * args.q)
    extra = args.pytest_args
    return forwarded + (extra[1:] if extra[:1] == ["--"] else extra)


def _rerun(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Re-run the latest run's failures with its device and opt-in flags."""
    if not args.artifacts_dir.is_dir():
        parser.error("--artifacts-dir must be an existing directory")
    run = latest_run(args.artifacts_dir)
    if run is None:
        print(f"No finished run found under {args.artifacts_dir}.", file=sys.stderr)
        return 1
    failed = failed_tests(run)
    if not failed:
        print(f"Latest run {run.get('run_id')} had no failures; nothing to rerun.")
        return 0
    explicit = _forward_options(args)
    if (run.get("target") or {}).get("kind") == "physical" and "--udid" not in explicit:
        parser.error("The latest run used a physical device; pass --udid and --team-id again")
    # Options given now win over the recorded ones.
    recorded = rerun_options(run, skip=set(explicit))
    print(f"Rerunning {len(failed)} failed test(s) from run {run.get('run_id')}:")
    for nodeid in failed:
        print(f"  {nodeid}")
    return run_suite(
        "rerun",
        recorded + explicit,
        args.artifacts_dir,
        args.email,
        args.email_preview,
        args.email_config,
        selection=failed,
    )


def format_devices(
    devices: list[SimulatorDevice], target: SimulatorDevice | None, reason: str
) -> str:
    """List available simulators by runtime, newest first, marking the run target."""
    lines = []
    if target is not None:
        lines += [
            f"Default target: {target.name} (iOS {target.platform_version}) {target.udid}",
            f"  Why: {reason}",
            "  Override with --device-name and/or --platform-version.",
        ]
    else:
        lines.append(f"No target: {reason}")
    runtime = None
    # Newest runtime first, names alphabetical within each runtime.
    ordered = sorted(devices, key=lambda device: device.name)
    ordered.sort(key=version_key, reverse=True)
    for device in ordered:
        if device.platform_version != runtime:
            runtime = device.platform_version
            lines += ["", f"iOS {runtime}"]
        marker = "→" if device == target else " "
        lines.append(f"  {marker} {device.name:<28} {device.state:<9} {device.udid}")
    return "\n".join(lines)


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
        "locators": "Report page locators that no longer match anything",
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
    rerun = commands.add_parser(
        "rerun", help="Re-run the latest run's failed tests on the same target", allow_abbrev=False
    )
    _add_run_options(rerun)
    history = commands.add_parser("history", help="Compare completed run manifests")
    history.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    history.add_argument("--limit", type=int, default=10)
    history.add_argument("--json", action="store_true")
    history.add_argument(
        "--flaky", action="store_true", help="Only tests that both passed and failed"
    )
    history.add_argument("--runs", type=int, help="Only the most recent N completed runs")
    devices = commands.add_parser(
        "devices", help="List simulators and show which one a run would use"
    )
    devices.add_argument("--device-name", help="Exact simulator name to resolve")
    devices.add_argument("--platform-version", help="Exact iOS runtime version to resolve")
    devices.add_argument("--json", action="store_true", help="Print machine-readable results")
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
    if args.command == "rerun":
        return _rerun(args, parser)
    if args.command == "history":
        if args.limit < 1:
            parser.error("--limit must be positive")
        if args.runs is not None and args.runs < 1:
            parser.error("--runs must be positive")
        if not args.artifacts_dir.is_dir():
            parser.error("--artifacts-dir must be an existing directory")
        history_report = summarize_history(args.artifacts_dir, args.runs)
        if args.json and args.flaky:
            history_report["tests"] = flaky_tests(history_report)
        print(
            json.dumps(history_report, indent=2)
            if args.json
            else format_history(history_report, args.limit, args.flaky)
        )
        return 0
    if args.command == "devices":
        available = [device for device in list_available_simulators() if device.is_available]
        target: SimulatorDevice | None = None
        try:
            target, reason = select_simulator(available, args.device_name, args.platform_version)
        except RuntimeError as error:
            reason = str(error)
        if args.json:
            print(
                json.dumps(
                    {
                        "target": asdict(target) if target else None,
                        "reason": reason,
                        "devices": [asdict(device) for device in available],
                    },
                    indent=2,
                )
            )
        else:
            print(format_devices(available, target, reason))
        if target is None:
            if args.json:
                print(reason, file=sys.stderr)
            return 1
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
