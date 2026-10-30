"""Helpers for discovering and preparing iOS simulators."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from itertools import takewhile
from pathlib import Path
from urllib.parse import quote

PREFERRED_SIMULATORS: tuple[tuple[str, str], ...] = (
    ("iPhone 18 Pro", "27.0"),
    ("iPhone 17 Pro", "26.4"),
    ("iPhone 16 Pro", "18.5"),
    ("iPhone 17 Pro", "26.2"),
    ("iPhone 17 Pro", "26.0"),
    ("iPhone 15", "17.0"),
)

DEFAULT_RESET_BUNDLE_IDS: tuple[str, ...] = (
    "com.apple.Preferences",
    "com.apple.mobilecal",
)

# iOS 27 asks Calendar and Maps for contacts through deferred system prompts that can
# surface over any app mid-run. A recorded denial keeps the prompt from appearing.
CONTACTS_DENIED_BUNDLE_IDS: tuple[str, ...] = (
    "com.apple.mobilecal",
    "com.apple.Maps",
)


@dataclass(frozen=True)
class SimulatorDevice:
    """Available iOS simulator device."""

    name: str
    udid: str
    platform_version: str
    state: str
    is_available: bool
    # simctl identifiers, needed to create a matching worker simulator.
    runtime_id: str = ""
    device_type_id: str = ""


def _runtime_version(runtime_name: str) -> str | None:
    """Extract iOS version from runtime name.

    Device-specific runtimes append a hardware suffix
    (``iOS-27-2-iPhone19-4``); only the leading numeric parts are the version.
    """
    prefix = "com.apple.CoreSimulator.SimRuntime.iOS-"
    if runtime_name.startswith(prefix):
        parts = runtime_name.removeprefix(prefix).split("-")
    elif runtime_name.startswith("iOS "):
        parts = runtime_name.removeprefix("iOS ").split(".")
    else:
        return None
    version = ".".join(takewhile(str.isdigit, parts))
    return version or None


def list_available_simulators() -> list[SimulatorDevice]:
    """Return all available iPhone simulators."""
    result = subprocess.run(  # noqa: S603
        ["xcrun", "simctl", "list", "devices", "available", "-j"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
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
                        runtime_id=runtime_name,
                        device_type_id=device.get("deviceTypeIdentifier", ""),
                    )
                )

    return simulators


def find_simulator(device_name: str, platform_version: str) -> SimulatorDevice | None:
    """Find exact simulator match."""
    for simulator in list_available_simulators():
        if (
            simulator.is_available
            and simulator.name == device_name
            and simulator.platform_version == platform_version
        ):
            return simulator
    return None


def get_preferred_simulator(
    device_name: str | None = None, platform_version: str | None = None
) -> SimulatorDevice:
    """Rank available simulators after applying all explicit target constraints."""
    return select_simulator(list_available_simulators(), device_name, platform_version)[0]


def select_simulator(
    devices: list[SimulatorDevice],
    device_name: str | None = None,
    platform_version: str | None = None,
) -> tuple[SimulatorDevice, str]:
    """Pick the run target from ``devices`` and say why it won.

    Raises:
        RuntimeError: If no available simulator satisfies the constraints.
    """
    available = [device for device in devices if device.is_available]
    simulators = [
        device
        for device in available
        if (device_name is None or device.name == device_name)
        and (platform_version is None or device.platform_version == platform_version)
        # Parallel-run workers are never a default target.
        and (device_name is not None or not device.name.startswith(WORKER_PREFIX))
    ]
    if not simulators:
        choices = ", ".join(
            sorted({f"{device.name} (iOS {device.platform_version})" for device in available})
        )
        raise RuntimeError(
            f"No available simulator matches name={device_name!r}, iOS={platform_version!r}. "
            f"Available: {choices or 'none'}."
        )
    constraints = [
        option
        for option, value in (
            ("--device-name", device_name),
            ("--platform-version", platform_version),
        )
        if value is not None
    ]
    matched = f"matches {' and '.join(constraints)}; " if constraints else ""

    # Model order decides first, so iPhone 18 Pro wins on any installed runtime.
    for preferred_name in dict.fromkeys(name for name, _ in PREFERRED_SIMULATORS):
        candidates = [device for device in simulators if device.name == preferred_name]
        if candidates:
            pinned = {version for name, version in PREFERRED_SIMULATORS if name == preferred_name}
            chosen = max(
                candidates,
                key=lambda device: (device.platform_version in pinned, version_key(device)),
            )
            runtime = (
                "its pinned runtime"
                if chosen.platform_version in pinned
                else "the newest installed runtime"
            )
            return chosen, f"{matched}highest-ranked preferred model, on {runtime}"

    chosen = max(simulators, key=lambda device: (version_key(device), device.name))
    if constraints:
        return chosen, f"{matched}newest matching runtime"
    return chosen, "no preferred model available; newest runtime"


def version_key(device: SimulatorDevice) -> tuple[int, ...]:
    """Order runtimes numerically so 27.10 sorts after 27.2."""
    return tuple(int(part) for part in device.platform_version.split("."))


WORKER_PREFIX = "UIAutomation Worker "


def worker_simulator_name(base: SimulatorDevice, slot: int) -> str:
    """Name a worker by slot, model, and runtime so different targets never share one."""
    return f"{WORKER_PREFIX}{slot} – {base.name} {base.platform_version}"


def ensure_worker_simulator(base: SimulatorDevice, slot: int) -> SimulatorDevice:
    """Return this slot's simulator of the same model and runtime, creating it once.

    Workers are kept between runs: a new simulator's first boot takes about 40 s and
    re-runs every app's first-launch onboarding, while a reboot takes a few seconds.
    """
    name = worker_simulator_name(base, slot)
    for device in list_available_simulators():
        if device.is_available and device.name == name and device.runtime_id == base.runtime_id:
            return device
    if not base.device_type_id or not base.runtime_id:
        raise RuntimeError(f"Cannot create a worker for {base.name}: simctl identifiers unknown.")
    udid = subprocess.run(  # noqa: S603
        ["xcrun", "simctl", "create", name, base.device_type_id, base.runtime_id],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout.strip()
    return SimulatorDevice(
        name, udid, base.platform_version, "Shutdown", True, base.runtime_id, base.device_type_id
    )


def boot_worker_simulator(base: SimulatorDevice, slot: int) -> SimulatorDevice:
    """Boot this slot's worker, recreating it if it cannot boot.

    Workers are disposable copies; an interrupted WebDriverAgent install can leave one
    that never finishes booting.
    """
    worker = ensure_worker_simulator(base, slot)
    stop_stray_wda(worker.udid)
    try:
        boot_simulator(worker.udid)
        return worker
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        subprocess.run(  # noqa: S603
            ["xcrun", "simctl", "shutdown", worker.udid],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        subprocess.run(  # noqa: S603
            ["xcrun", "simctl", "delete", worker.udid],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    worker = ensure_worker_simulator(base, slot)
    boot_simulator(worker.udid)
    return worker


def stop_stray_wda(udid: str) -> None:
    """Stop WebDriverAgent ``xcodebuild`` runs left on this simulator by an interrupted run.

    When a session start is interrupted, its ``xcodebuild test-without-building`` outlives
    Appium and holds the device, so later ``simctl`` calls hang. Appium only clears these
    when its next session starts, after our simulator reset has already blocked.
    """
    subprocess.run(  # noqa: S603
        ["pkill", "-f", f"xcodebuild.*{udid}"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def boot_simulator(udid: str) -> None:
    """Boot simulator if needed and wait until fully started."""
    subprocess.run(
        ["xcrun", "simctl", "boot", udid],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )  # noqa: S603
    subprocess.run(  # noqa: S603
        ["xcrun", "simctl", "bootstatus", udid, "-b"],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )


def shutdown_simulator(udid: str) -> None:
    """Shut down a running simulator, reporting failures to the caller."""
    subprocess.run(  # noqa: S603
        ["xcrun", "simctl", "shutdown", udid],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def reset_simulator_app_state(
    udid: str,
    bundle_ids: tuple[str, ...] = DEFAULT_RESET_BUNDLE_IDS,
) -> None:
    """Terminate apps, reset permissions, then deny contacts to apps that would prompt.

    Persisted app data is not erased.
    """
    for bundle_id in bundle_ids:
        subprocess.run(  # noqa: S603
            ["xcrun", "simctl", "terminate", udid, bundle_id],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        subprocess.run(  # noqa: S603
            ["xcrun", "simctl", "privacy", udid, "reset", "all", bundle_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    # After the resets, which would otherwise clear Calendar's contacts denial.
    for bundle_id in CONTACTS_DENIED_BUNDLE_IDS:
        subprocess.run(  # noqa: S603
            ["xcrun", "simctl", "privacy", udid, "revoke", "contacts", bundle_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )


def reset_location_permission(udid: str, bundle_id: str) -> None:
    """Forget an app's location decision so its permission prompt appears again."""
    subprocess.run(  # noqa: S603
        ["xcrun", "simctl", "privacy", udid, "reset", "location", bundle_id],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def set_simulator_location(udid: str, latitude: float, longitude: float) -> None:
    """Simulate a fixed device location until it is cleared."""
    subprocess.run(  # noqa: S603
        ["xcrun", "simctl", "location", udid, "set", f"{latitude},{longitude}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def clear_simulator_location(udid: str) -> None:
    """Stop simulating a device location."""
    subprocess.run(  # noqa: S603
        ["xcrun", "simctl", "location", udid, "clear"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def open_simulator_app(udid: str) -> None:
    """Open the selected Xcode's Device Hub focused on the target simulator."""
    developer_dir = os.environ.get("DEVELOPER_DIR")
    if not developer_dir:
        developer_dir = subprocess.run(
            ["xcode-select", "-p"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
    developer_path = Path(developer_dir)
    if developer_path.suffix == ".app":
        developer_path = developer_path / "Contents" / "Developer"
    device_hub = developer_path.parent / "Applications" / "DeviceHub.app"
    if not device_hub.is_dir():
        raise RuntimeError(
            f"Device Hub not found at {device_hub}. Select Xcode 27 or newer, "
            "or use --headless-simulator to run without a window."
        )
    subprocess.run(  # noqa: S603
        ["open", "-a", str(device_hub), f"devices:///manage/select?id={quote(udid, safe='')}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
