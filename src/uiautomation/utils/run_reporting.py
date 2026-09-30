"""Portable run metadata and pytest result recording without device mutations."""

import json
import logging
import platform
import subprocess
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import monotonic
from typing import Any

LOGGER = logging.getLogger(__name__)


def working_tree_dirty(repository: Path) -> bool | None:
    """Report tracked/untracked edits without recording filenames or content."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=repository,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return bool(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return None


# An allowlist prevents arbitrary provider credentials and personal identifiers
# from reaching reports, including unknown future capability names.
PUBLIC_CAPABILITIES = {
    "platformName",
    "platformVersion",
    "deviceName",
    "automationName",
    "bundleId",
    "noReset",
    "fullReset",
    "isHeadless",
    "newCommandTimeout",
    "language",
    "locale",
}


def sanitized_capabilities(capabilities: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only known noncredential capability fields and primitive values."""
    result: dict[str, Any] = {}
    for key, value in capabilities.items():
        if key == "appium:options" and isinstance(value, Mapping):
            result[key] = sanitized_capabilities(value)
        elif key.removeprefix("appium:") in PUBLIC_CAPABILITIES and isinstance(
            value, (str, bool, int, float, type(None))
        ):
            result[key] = value
    return result


def _command_output(command: list[str], cwd: Path) -> str | None:
    """Read a bounded version probe; missing tools remain unavailable."""
    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, check=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def collect_environment(repository: Path, integration: bool) -> dict[str, Any]:
    """Capture tool versions, probing native tools only for integration runs."""
    packages: dict[str, str | None] = {}
    for package in ("uiautomation", "Appium-Python-Client", "selenium", "pytest"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = None
    tools: dict[str, str | None] = {}
    if integration:
        tools["xcode"] = _command_output(["xcodebuild", "-version"], repository)
        tools["appium"] = _command_output(["appium", "--version"], repository)
        raw_drivers = _command_output(
            ["appium", "driver", "list", "--installed", "--json"], repository
        )
        try:
            drivers = json.loads(raw_drivers or "{}")
            xcuitest = drivers.get("xcuitest", {})
            tools["xcuitest"] = xcuitest.get("version") or xcuitest.get("driverVersion")
        except (AttributeError, TypeError, ValueError):
            tools["xcuitest"] = None
    return {
        "commit": _command_output(["git", "rev-parse", "HEAD"], repository),
        "working_tree_dirty": working_tree_dirty(repository),
        "python": platform.python_version(),
        "host_platform": platform.system(),
        "packages": packages,
        "tools": tools,
        "tool_version_scope": "local host; external Appium server versions may differ",
    }


class RunReport:
    """Record serial or controller-side pytest results in a durable manifest."""

    def __init__(
        self, root: Path, repository: Path, integration: bool, requested_target: dict[str, Any]
    ) -> None:
        self.root = root
        self.repository = repository
        self.integration = integration
        self.started = monotonic()
        self.enabled = False
        self.manifest: dict[str, Any] = {
            "schema_version": 1,
            "run_id": root.name,
            "integration": integration,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "target": requested_target,
            "capabilities": {},
            "results": [],
        }

    def pytest_sessionstart(self, session: Any) -> None:
        """Initialize metadata without launching a simulator or Appium."""
        if session.config.option.collectonly:
            return
        self.enabled = True
        self.manifest["environment"] = collect_environment(self.repository, self.integration)
        self.manifest["worker"] = getattr(session.config, "workerinput", {}).get("workerid")
        options = session.config.option
        self.manifest["options"] = {
            name: value
            for name in (
                "run_integration",
                "run_diagnostics",
                "run_lifecycle",
                "run_maps_navigation",
                "headless_simulator",
                "restart_simulator",
                "no_reset",
                "skip_simulator_state_reset",
                "timeout",
                "numprocesses",
            )
            if isinstance((value := getattr(options, name, None)), (bool, int, float))
        }
        self.write()

    def pytest_collection_finish(self, session: Any) -> None:
        """Record selected repository tests without parameter values or raw CLI text."""
        self.record_selection([item.nodeid for item in session.items])

    def record_selection(self, nodeids: list[str]) -> None:
        """Record serial or xdist worker collection without parameter values."""
        selected = []
        for raw_nodeid in nodeids:
            nodeid = raw_nodeid.split("[", 1)[0]
            filename, _, test_name = nodeid.partition("::")
            path = (self.repository / filename).resolve()
            if path.is_relative_to(self.repository.resolve()):
                selected.append(
                    f"{path.relative_to(self.repository.resolve()).as_posix()}::{test_name}"
                )
        self.manifest["selection"] = {
            "tests": sorted(set(selected)),
            "collected_cases": len(nodeids),
            "parameter_values_omitted": True,
        }
        self.write()

    def set_target(self, name: str, platform_version: str) -> None:
        """Replace automatic target requests with the resolved device/runtime."""
        self.manifest["target"].update(device_name=name, platform_version=platform_version)
        self.write()

    def set_capabilities(self, capabilities: Mapping[str, Any]) -> None:
        """Store only allowlisted negotiated capability values."""
        self.manifest["capabilities"] = sanitized_capabilities(capabilities)
        for field, name in (("deviceName", "device_name"), ("platformVersion", "platform_version")):
            value = capabilities.get(f"appium:{field}", capabilities.get(field))
            if isinstance(value, str):
                self.manifest["target"][name] = value
        self.write()

    def pytest_runtest_logreport(self, report: Any) -> None:
        """Preserve all phases; teardown failures must remain visible."""
        self.manifest["results"].append(
            {
                "nodeid": report.nodeid,
                "phase": report.when,
                "outcome": report.outcome,
                "duration_seconds": round(report.duration, 6),
                "artifacts": [
                    value for name, value in report.user_properties if name == "failure_artifacts"
                ],
            }
        )
        self.write()

    def pytest_sessionfinish(self, session: Any, exitstatus: int) -> None:
        """Finalize elapsed time and one combined outcome per test."""
        outcomes: dict[str, str] = {}
        for result in self.manifest["results"]:
            previous = outcomes.get(result["nodeid"])
            if previous == "failed":
                continue
            if result["outcome"] == "failed" or result["phase"] == "call":
                outcomes[result["nodeid"]] = result["outcome"]
            elif result["outcome"] == "skipped" and previous is None:
                outcomes[result["nodeid"]] = "skipped"
        self.manifest.update(
            finished_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=round(monotonic() - self.started, 6),
            exit_status=int(exitstatus),
            summary=dict(Counter(outcomes.values())),
        )
        self.write()

    def write(self) -> None:
        """Persist best effort so reporting never changes the test outcome."""
        if not self.enabled:
            return
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            temporary = self.root / "run.json.tmp"
            temporary.write_text(json.dumps(self.manifest, indent=2), encoding="utf-8")
            temporary.replace(self.root / "run.json")
        except (OSError, TypeError, ValueError):
            LOGGER.exception("Unable to save run manifest")
