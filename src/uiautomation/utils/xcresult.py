"""Read Xcode result bundles (.xcresult) from the Swift suite into run-manifest form."""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Marks a manifest's test IDs as Swift tests, e.g. "swift::RemindersTests/testHomeIsReady".
NODE_PREFIX = "swift::"
RUNNER = "xcuitest"
# Name given to the screenshot the Swift base test case attaches to every failure.
FAILURE_SCREENSHOT = "Failure screenshot"

_OUTCOMES = {
    "Passed": "passed",
    "Failed": "failed",
    "Skipped": "skipped",
    # XCTExpectFailure: the test behaved as its author predicted.
    "Expected Failure": "passed",
}


@dataclass(frozen=True)
class SwiftTest:
    """One XCTest method's result."""

    suite: str
    name: str
    outcome: str
    duration_seconds: float
    messages: tuple[str, ...] = ()
    location: str | None = None

    @property
    def identifier(self) -> str:
        """Xcode's identifier for the test, as used in result bundles."""
        return f"{self.suite}/{self.name}()"

    @property
    def nodeid(self) -> str:
        """The test's ID in run manifests, kept distinct from pytest node IDs."""
        return f"{NODE_PREFIX}{self.suite}/{self.name}"


def read_test_results(bundle: Path, kind: str) -> dict[str, Any]:
    """Run ``xcresulttool get test-results <kind>`` on a bundle and parse its JSON.

    Args:
        bundle: Path to an ``.xcresult`` bundle.
        kind: ``summary`` or ``tests``.
    """
    result = subprocess.run(  # noqa: S603
        ["xcrun", "xcresulttool", "get", "test-results", kind, "--path", str(bundle), "--compact"],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected xcresulttool {kind} output")
    return data


def flatten_tests(tests: dict[str, Any]) -> list[SwiftTest]:
    """Collect every test case from xcresulttool's nested plan/bundle/suite tree."""
    found: list[SwiftTest] = []

    def walk(node: Any, suite: str) -> None:
        if not isinstance(node, dict):
            return
        kind = node.get("nodeType")
        children = node.get("children") or []
        if kind == "Test Case":
            notes = [
                child
                for child in children
                if isinstance(child, dict)
                and child.get("nodeType") in ("Failure Message", "Skip Message")
            ]
            location = None
            for note in notes:
                source = note.get("sourceLocation")
                if isinstance(source, dict) and source.get("filePath"):
                    location = f"{Path(str(source['filePath'])).name}:{source.get('lineNumber')}"
                    break
            duration = node.get("durationInSeconds")
            found.append(
                SwiftTest(
                    suite=suite,
                    name=str(node.get("name") or "").removesuffix("()"),
                    # An unknown result must not pass silently.
                    outcome=_OUTCOMES.get(str(node.get("result")), "failed"),
                    duration_seconds=float(duration) if isinstance(duration, int | float) else 0.0,
                    messages=tuple(str(note.get("name") or "") for note in notes),
                    location=location,
                )
            )
            return
        if kind == "Test Suite":
            suite = str(node.get("name") or suite)
        for child in children:
            walk(child, suite)

    for node in tests.get("testNodes") or []:
        walk(node, "")
    return found


def _iso(timestamp: Any) -> str | None:
    """Convert xcresulttool's epoch seconds to the manifests' ISO 8601 UTC form."""
    if not isinstance(timestamp, int | float):
        return None
    return datetime.fromtimestamp(timestamp, UTC).isoformat()


def build_manifest(
    summary: dict[str, Any],
    tests: list[SwiftTest],
    *,
    run_id: str,
    exit_status: int,
    options: dict[str, Any],
    environment: dict[str, Any],
) -> dict[str, Any]:
    """Describe a Swift run in the same shape as a pytest run's ``run.json``.

    The shared shape lets ``uiautomation history`` and the email summary read Swift runs.
    ``runner`` tells the pytest-only ``rerun`` command to leave them alone.
    """
    device: dict[str, Any] = {}
    for entry in summary.get("devicesAndConfigurations") or []:
        if isinstance(entry, dict) and isinstance(entry.get("device"), dict):
            device = entry["device"]
            break
    start, finish = summary.get("startTime"), summary.get("finishTime")
    duration = (
        round(finish - start, 6)
        if isinstance(start, int | float) and isinstance(finish, int | float)
        else round(sum(test.duration_seconds for test in tests), 6)
    )
    return {
        "schema_version": 1,
        "runner": RUNNER,
        "run_id": run_id,
        "integration": True,
        "started_at": _iso(start),
        "finished_at": _iso(finish) or datetime.now(UTC).isoformat(),
        "duration_seconds": duration,
        "exit_status": exit_status,
        "target": {
            "kind": "simulator" if "Simulator" in str(device.get("platform")) else "physical",
            "device_name": device.get("deviceName"),
            "platform_version": device.get("osVersion"),
            "model": device.get("modelName"),
        },
        "capabilities": {},
        "worker": None,
        "options": options,
        "environment": environment,
        "selection": {"tests": sorted(test.nodeid for test in tests)},
        "results": [
            {
                "nodeid": test.nodeid,
                "phase": "call",
                "outcome": test.outcome,
                "duration_seconds": round(test.duration_seconds, 6),
                "artifacts": [],
            }
            for test in tests
        ],
        "summary": dict(Counter(test.outcome for test in tests)),
    }


def export_failure_screenshots(bundle: Path, destination: Path) -> dict[str, Path]:
    """Export each failed test's screenshot from a bundle.

    Returns:
        Screenshot files keyed by Xcode test identifier (``Suite/testName()``). Tests
        without an exported screenshot are absent.
    """
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # noqa: S603
        [
            "xcrun",
            "xcresulttool",
            "export",
            "attachments",
            "--path",
            str(bundle),
            "--output-path",
            str(destination),
            # Failures also carry a screen recording of several megabytes; leave it behind.
            "--filter",
            f"{FAILURE_SCREENSHOT}*",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=300,
    )
    return screenshots_from_manifest(
        json.loads((destination / "manifest.json").read_text(encoding="utf-8")), destination
    )


def screenshots_from_manifest(manifest: Any, directory: Path) -> dict[str, Path]:
    """Pick each test's first failure screenshot from an attachment export manifest."""
    screenshots: dict[str, Path] = {}
    if not isinstance(manifest, list):
        return screenshots
    for entry in manifest:
        if not isinstance(entry, dict) or not isinstance(entry.get("testIdentifier"), str):
            continue
        for attachment in entry.get("attachments") or []:
            if not isinstance(attachment, dict):
                continue
            name = str(attachment.get("suggestedHumanReadableName") or "")
            filename = attachment.get("exportedFileName")
            if not name.startswith(FAILURE_SCREENSHOT) or not isinstance(filename, str):
                continue
            # Only plain file names: a manifest must not point outside the export folder.
            path = directory / Path(filename).name
            if path.is_file():
                screenshots.setdefault(entry["testIdentifier"], path)
    return screenshots
