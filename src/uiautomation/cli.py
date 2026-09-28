"""Command-line tools for the UIAutomation framework."""

from __future__ import annotations

import argparse
import json

from uiautomation.utils.doctor import diagnose_environment, format_report


def main(argv: list[str] | None = None) -> int:
    """Run a framework command and return its process exit code."""
    parser = argparse.ArgumentParser(prog="uiautomation")
    commands = parser.add_subparsers(dest="command", required=True)
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
