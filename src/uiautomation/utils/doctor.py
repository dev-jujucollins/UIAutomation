"""Bounded environment diagnostics for local iOS simulator testing."""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import urlopen

from uiautomation.utils.appium_service import get_appium_executable, is_local_appium_url
from uiautomation.utils.simulator_control import (
    SimulatorDevice,
    get_preferred_simulator,
    list_available_simulators,
)


@dataclass(frozen=True)
class DoctorCheck:
    """A diagnostic result and actionable guidance when needed."""

    name: str
    status: Literal["pass", "warn", "fail"]
    detail: str
    remedy: str | None = None


@dataclass
class DoctorReport:
    """Environment check results suitable for terminal or JSON output."""

    checks: list[DoctorCheck] = field(default_factory=list)
    simulators: list[SimulatorDevice] = field(default_factory=list)
    selected_simulator: SimulatorDevice | None = None

    @property
    def ok(self) -> bool:
        """Return whether every required check passed."""
        return all(check.status != "fail" for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        """Return JSON-compatible results, including overall readiness."""
        return {"ok": self.ok, **asdict(self)}


def _command(command: list[str], timeout: int = 30, include_stderr: bool = False) -> str:
    """Run a bounded command without a shell and preserve useful errors."""
    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.CalledProcessError as error:
        output = (error.stderr or error.stdout or str(error)).strip()
        raise RuntimeError(output) from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Timed out after {timeout}s: {' '.join(command)}") from error
    return "\n".join(
        output.strip()
        for output in (result.stdout, result.stderr if include_stderr else "")
        if output
    ).strip()


def _check_xcode(report: DoctorReport, headless: bool) -> None:
    """Check the selected Xcode and, when needed, Device Hub."""
    remedy = "Install/select Xcode 27+ in Xcode Settings > Locations; open Xcode to finish setup."
    try:
        developer = os.environ.get("DEVELOPER_DIR") or _command(["xcode-select", "-p"])
        if not developer:
            raise RuntimeError("No selected developer directory.")
        developer_path = Path(developer)
        if developer_path.suffix == ".app":
            developer_path = developer_path / "Contents" / "Developer"
        version = _command(["xcodebuild", "-version"])
        match = re.search(r"^Xcode (\d+)", version, re.MULTILINE)
        if match is None or int(match.group(1)) < 27:
            raise RuntimeError(f"Xcode 27+ required; found {version or 'unknown version'}.")
        report.checks.append(DoctorCheck("Xcode", "pass", f"{version}\n{developer_path}"))
        hub = developer_path.parent / "Applications" / "DeviceHub.app"
        if hub.is_dir():
            report.checks.append(DoctorCheck("Device Hub", "pass", str(hub)))
        elif headless:
            report.checks.append(
                DoctorCheck("Device Hub", "warn", "Not found; headless mode does not open it.")
            )
        else:
            report.checks.append(
                DoctorCheck(
                    "Device Hub",
                    "fail",
                    f"Not found at {hub}.",
                    "Select a complete Xcode 27+ installation or use --headless-simulator.",
                )
            )
    except (OSError, RuntimeError) as error:
        report.checks.append(DoctorCheck("Xcode", "fail", str(error), remedy))


def _check_simulators(
    report: DoctorReport, device_name: str | None, platform_version: str | None
) -> None:
    """Report available targets and use the framework's selection policy."""
    try:
        report.simulators = [
            device for device in list_available_simulators() if device.is_available
        ]
        report.selected_simulator = get_preferred_simulator(device_name, platform_version)
        selected = report.selected_simulator
        report.checks.append(
            DoctorCheck(
                "Simulator",
                "pass",
                f"{selected.name}, iOS {selected.platform_version}, {selected.state} ({selected.udid})",
            )
        )
    except (
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
        ValueError,
        TypeError,
        KeyError,
    ) as error:
        report.checks.append(
            DoctorCheck(
                "Simulator",
                "fail",
                str(error),
                "Install an iOS runtime in Xcode Settings and create an iPhone in Device Hub; "
                "check --device-name and --platform-version. If CoreSimulator is inaccessible, "
                "run from a terminal with access to the local simulator service.",
            )
        )


def _check_appium(report: DoctorReport, run_driver_doctor: bool) -> None:
    """Check Appium and the driver, optionally invoking upstream diagnostics."""
    try:
        executable = get_appium_executable()
        version = _command([executable, "--version"])
        report.checks.append(DoctorCheck("Appium", "pass", f"{version} ({executable})"))
    except (OSError, RuntimeError) as error:
        report.checks.append(
            DoctorCheck(
                "Appium", "fail", str(error), "Install Appium with `npm install -g appium`."
            )
        )
        return
    try:
        payload = json.loads(_command([executable, "driver", "list", "--installed", "--json"]))
        driver = payload.get("xcuitest", {}) if isinstance(payload, dict) else {}
        if not isinstance(driver, dict) or driver.get("installed") is not True:
            raise RuntimeError("XCUITest driver is not installed.")
        report.checks.append(DoctorCheck("XCUITest", "pass", str(driver.get("version", "unknown"))))
    except (OSError, RuntimeError, ValueError) as error:
        report.checks.append(
            DoctorCheck(
                "XCUITest",
                "fail",
                str(error),
                "Run `appium driver install xcuitest`; ensure APPIUM_HOME is accessible.",
            )
        )
        return
    if not run_driver_doctor:
        report.checks.append(
            DoctorCheck(
                "XCUITest doctor",
                "warn",
                "Not run: upstream diagnostics may apply fixes or start a device tunnel.",
                "Use --run-driver-doctor to opt in to `appium driver doctor xcuitest` (60s limit).",
            )
        )
        return
    try:
        output = _command(
            [executable, "driver", "doctor", "xcuitest"], timeout=60, include_stderr=True
        )
        report.checks.append(
            DoctorCheck("XCUITest doctor", "pass", output or "Required upstream checks passed.")
        )
    except (OSError, RuntimeError) as error:
        report.checks.append(
            DoctorCheck(
                "XCUITest doctor",
                "fail",
                str(error),
                "Review upstream diagnostics with `appium driver doctor xcuitest`.",
            )
        )


def _check_server(report: DoctorReport, server_url: str, require_server: bool) -> None:
    """Validate Appium's readiness payload, preserving custom base paths."""
    try:
        parsed = urlparse(server_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Use a full http:// or https:// Appium URL.")
        if parsed.query or parsed.fragment:
            raise ValueError("Appium server URL must not contain a query or fragment.")
        _ = parsed.port  # Validate the port before attempting a connection.
    except ValueError as error:
        report.checks.append(DoctorCheck("Appium server", "fail", str(error)))
        return
    local = is_local_appium_url(server_url)
    status_url = f"{server_url.rstrip('/')}/status"
    try:
        with urlopen(status_url, timeout=3) as response:  # noqa: S310
            payload = json.load(response)
            value = payload.get("value", {}) if isinstance(payload, dict) else {}
            if (
                response.status != 200
                or not isinstance(value, dict)
                or value.get("ready") is not True
            ):
                raise ValueError("Endpoint did not report value.ready=true.")
        report.checks.append(DoctorCheck("Appium server", "pass", f"Ready at {status_url}"))
    except (OSError, ValueError) as error:
        report.checks.append(
            DoctorCheck(
                "Appium server",
                "fail"
                if require_server or not local or isinstance(error, (ValueError, HTTPError))
                else "warn",
                f"Not ready at {status_url}: {error}",
                "Start Appium or check the URL/base path. Local integration tests can start "
                "Appium automatically; use --require-server to make readiness mandatory.",
            )
        )


def diagnose_environment(
    *,
    device_name: str | None = None,
    platform_version: str | None = None,
    server_url: str = "http://localhost:4723",
    headless: bool = False,
    require_server: bool = False,
    run_driver_doctor: bool = False,
) -> DoctorReport:
    """Inspect local simulator prerequisites without starting an iOS session.

    Args:
        device_name: Optional exact simulator name, as in pytest.
        platform_version: Optional exact iOS runtime, as in pytest.
        server_url: Appium base URL, including any custom base path.
        headless: Whether Device Hub is unnecessary for the intended run.
        require_server: Treat an unavailable local server as a required failure.
        run_driver_doctor: Opt in to upstream diagnostics, which may apply fixes.

    Returns:
        Results with failed required checks and actionable next steps.
    """
    report = DoctorReport()
    macos = platform.system() == "Darwin"
    report.checks.append(
        DoctorCheck(
            "Host",
            "pass" if macos else "fail",
            f"{platform.system()} {platform.release()}, Python {platform.python_version()}",
            None if macos else "Use macOS for local iOS integration tests; unit tests work here.",
        )
    )
    try:
        report.checks.append(DoctorCheck("Node.js", "pass", _command(["node", "--version"])))
    except (OSError, RuntimeError) as error:
        report.checks.append(
            DoctorCheck(
                "Node.js", "fail", str(error), "Install a Node.js version supported by Appium."
            )
        )
    _check_xcode(report, headless)
    _check_simulators(report, device_name, platform_version)
    _check_appium(report, run_driver_doctor)
    _check_server(report, server_url, require_server)
    return report


def format_report(report: DoctorReport) -> str:
    """Render concise results and available simulator choices."""
    lines = ["UIAutomation environment doctor"]
    for check in report.checks:
        lines.append(f"[{check.status.upper()}] {check.name}: {check.detail}")
        if check.remedy:
            lines.append(f"  Next: {check.remedy}")
    if report.simulators:
        lines.append("Available iPhone simulators:")
        for device in report.simulators:
            lines.append(
                f"  {device.name} | iOS {device.platform_version} | {device.state} | {device.udid}"
            )
    failures = sum(check.status == "fail" for check in report.checks)
    warnings = sum(check.status == "warn" for check in report.checks)
    lines.append(
        f"Result: {failures} failed, {warnings} warning(s). No iOS test session was started."
    )
    return "\n".join(lines)
