"""Helpers for discovering and preparing iOS simulators."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

PREFERRED_SIMULATORS: tuple[tuple[str, str], ...] = (
    ("iPhone 17 Pro", "26.4"),
    ("iPhone 16 Pro", "18.5"),
    ("iPhone 17 Pro", "26.2"),
    ("iPhone 17 Pro", "26.0"),
    ("iPhone 15", "17.0"),
)


@dataclass(frozen=True)
class SimulatorDevice:
    """Available iOS simulator device."""

    name: str
    udid: str
    platform_version: str
    state: str
    is_available: bool


def _runtime_version(runtime_name: str) -> str | None:
    """Extract iOS version from runtime name."""
    prefix = "com.apple.CoreSimulator.SimRuntime.iOS-"
    if runtime_name.startswith(prefix):
        return runtime_name.removeprefix(prefix).replace("-", ".")
    if runtime_name.startswith("iOS "):
        return runtime_name.removeprefix("iOS ")
    return None


def list_available_simulators() -> list[SimulatorDevice]:
    """Return all available iPhone simulators."""
    result = subprocess.run(  # noqa: S603
        ["xcrun", "simctl", "list", "devices", "available", "-j"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    simulators: list[SimulatorDevice] = []

    for runtime_name, devices in payload.get("devices", {}).items():
        platform_version = _runtime_version(runtime_name)
        if platform_version is None:
            continue

        for device in devices:
            if device.get("deviceTypeIdentifier", "").startswith(
                "com.apple.CoreSimulator.SimDeviceType.iPhone"
            ) or device.get("name", "").startswith("iPhone"):
                simulators.append(
                    SimulatorDevice(
                        name=device["name"],
                        udid=device["udid"],
                        platform_version=platform_version,
                        state=device["state"],
                        is_available=device.get("isAvailable", True),
                    )
                )

    return simulators


def find_simulator(device_name: str, platform_version: str) -> SimulatorDevice | None:
    """Find exact simulator match."""
    for simulator in list_available_simulators():
        if simulator.name == device_name and simulator.platform_version == platform_version:
            return simulator
    return None


def get_preferred_simulator() -> SimulatorDevice:
    """Return best available simulator for local development."""
    simulators = list_available_simulators()

    for name, version in PREFERRED_SIMULATORS:
        for simulator in simulators:
            if simulator.name == name and simulator.platform_version == version:
                return simulator

    if simulators:
        ranked = sorted(
            simulators,
            key=lambda simulator: (
                tuple(int(part) for part in simulator.platform_version.split(".")),
                simulator.name,
            ),
            reverse=True,
        )
        return ranked[0]

    raise RuntimeError("No available iOS simulators found.")


def boot_simulator(udid: str) -> None:
    """Boot simulator if needed and wait until fully started."""
    subprocess.run(
        ["xcrun", "simctl", "boot", udid],
        check=False,
        capture_output=True,
        text=True,
    )  # noqa: S603
    subprocess.run(  # noqa: S603
        ["xcrun", "simctl", "bootstatus", udid, "-b"],
        check=True,
        capture_output=True,
        text=True,
    )


def open_simulator_app(udid: str) -> None:
    """Open Simulator app focused on target device."""
    subprocess.run(  # noqa: S603
        ["open", "-a", "Simulator", "--args", "-CurrentDeviceUDID", udid],
        check=True,
        capture_output=True,
        text=True,
    )
