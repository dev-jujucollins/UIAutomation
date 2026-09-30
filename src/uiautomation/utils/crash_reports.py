"""Collect recent Apple IPS reports only for the selected simulator and app."""

import json
import shutil
from pathlib import Path
from time import monotonic, time
from uuid import UUID


def collect_simulator_crashes(
    destination: Path, udid: str, bundle_id: str, since: float, home: Path | None = None
) -> list[str]:
    """Copy matching IPS reports, bounded to five files and a two-second scan.

    Host reports require simulator identity in their metadata. Simulator-local
    reports are already scoped by directory. Missing/late reports are optional.
    Returns capture errors without changing the original test outcome.
    """
    UUID(udid)
    home = home or Path.home()
    simulator = home / "Library/Developer/CoreSimulator/Devices" / udid
    if not simulator.is_dir():
        return []
    directories = [
        (home / "Library/Logs/DiagnosticReports", False),
        (simulator / "data/Library/Logs/CrashReporter", True),
    ]
    errors: list[str] = []
    copied = 0
    deadline = monotonic() + 2
    now = time()
    for directory, scoped in directories:
        if not directory.is_dir():
            continue
        try:
            for source in directory.glob("*.ips"):
                if copied >= 5 or monotonic() >= deadline:
                    return errors
                try:
                    stat = source.stat()
                    if (
                        source.is_symlink()
                        or not since <= stat.st_mtime <= now
                        or stat.st_size > 10_000_000
                    ):
                        continue
                    content = source.read_text(encoding="utf-8")
                    header, end = json.JSONDecoder().raw_decode(content)
                    remainder = content[end:].strip()
                    body = json.loads(remainder) if remainder else header
                    if not isinstance(header, dict) or not isinstance(body, dict):
                        continue
                    bundle = body.get("bundleInfo", {})
                    actual_bundle = (
                        bundle.get("CFBundleIdentifier") if isinstance(bundle, dict) else None
                    )
                    if (actual_bundle or header.get("bundleID")) != bundle_id:
                        continue
                    coalition = str(body.get("coalitionName", "")).lower()
                    process_path = str(body.get("procPath", "")).lower()
                    if not scoped and not (
                        coalition == f"com.apple.coresimulator.simdevice.{udid.lower()}"
                        or f"/devices/{udid.lower()}/" in process_path
                    ):
                        continue
                    shutil.copyfile(source, destination / f"crash-{copied + 1}.ips")
                    copied += 1
                except (OSError, ValueError) as error:
                    errors.append(f"Crash report capture: {type(error).__name__}")
        except OSError as error:
            errors.append(f"Crash report directory: {type(error).__name__}")
    return errors
