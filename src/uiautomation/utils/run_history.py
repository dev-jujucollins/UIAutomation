"""Compare completed controller manifests without retrying tests."""

import json
from collections import defaultdict
from collections.abc import Set as AbstractSet
from itertools import pairwise
from pathlib import Path
from statistics import median
from typing import Any


def summarize_history(root: Path, last_runs: int | None = None) -> dict[str, Any]:
    """Group results by test and target; mixed outcomes are candidates, not proof of flakiness.

    Args:
        root: Directory searched recursively for ``run.json`` manifests.
        last_runs: Keep only this many most recently finished runs; None keeps all.
    """
    runs: list[tuple[str, str, tuple[str, str, str], dict[str, dict[str, Any]]]] = []
    seen: set[str] = set()
    ignored = 0
    for path in sorted(root.rglob("run.json")):
        try:
            if path.stat().st_size > 20_000_000:
                raise ValueError("Manifest too large")
            run = json.loads(path.read_text())
            if (
                not isinstance(run, dict)
                or not run.get("finished_at")
                or run.get("worker") is not None
            ):
                ignored += 1
                continue
            run_id = run["run_id"]
            if not isinstance(run_id, str) or run_id in seen:
                ignored += 1
                continue
            target = run["target"]
            identity = (
                "unit" if run.get("integration") is False else str(target.get("kind") or "unknown"),
                str(target.get("device_name") or "unknown"),
                str(target.get("platform_version") or "unknown"),
            )
            tests: dict[str, dict[str, Any]] = {}
            for result in run["results"]:
                nodeid, phase, outcome = result["nodeid"], result["phase"], result["outcome"]
                duration = float(result["duration_seconds"])
                if (
                    not isinstance(nodeid, str)
                    or phase not in {"setup", "call", "teardown"}
                    or outcome not in {"passed", "failed", "skipped"}
                    or not 0 <= duration < float("inf")
                ):
                    raise ValueError("Invalid phase record")
                test = tests.setdefault(nodeid, {"outcome": None, "total": 0.0, "setup": 0.0})
                test["total"] += duration
                if phase == "setup":
                    test["setup"] += duration
                if test["outcome"] != "failed":
                    if outcome == "failed" or phase == "call" or outcome == "skipped":
                        test["outcome"] = outcome
            runs.append((str(run["finished_at"]), run_id, identity, tests))
            seen.add(run_id)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            ignored += 1
    # ISO 8601 UTC timestamps sort chronologically as strings.
    runs.sort(key=lambda run: (run[0], run[1]))
    if last_runs is not None:
        runs = runs[-last_runs:]
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for _, _, identity, tests in runs:
        for nodeid, test in tests.items():
            if test["outcome"] is not None:
                groups[(*identity, nodeid)].append(test)
    rows = []
    for (kind, device, runtime, nodeid), results in groups.items():
        passed = sum(result["outcome"] == "passed" for result in results)
        failed = sum(result["outcome"] == "failed" for result in results)
        decisive = [result["outcome"] for result in results if result["outcome"] != "skipped"]
        rows.append(
            {
                "nodeid": nodeid,
                "kind": kind,
                "device": device,
                "runtime": runtime,
                "runs": len(results),
                "passed": passed,
                "failed": failed,
                # Skips say nothing about stability, so they are left out of the rate.
                "fail_rate": round(failed / (passed + failed), 3) if passed + failed else None,
                "mixed_outcomes": bool(passed and failed),
                # Oldest first, e.g. "PPFPF".
                "outcomes": "".join(result["outcome"][0].upper() for result in results),
                # Pass/fail changes, skips ignored. A fixed regression ("FFPP") flips once;
                # a flaky test keeps flipping.
                "flips": sum(a != b for a, b in pairwise(decisive)),
                "median_seconds": round(median(result["total"] for result in results), 3),
                "median_setup_seconds": round(median(result["setup"] for result in results), 3),
            }
        )
    rows.sort(key=lambda row: (-row["failed"], -row["median_seconds"], row["nodeid"]))
    return {"completed_runs": len(runs), "ignored_manifests": ignored, "tests": rows}


def flaky_tests(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Tests that both passed and failed on the same target, most pass/fail flips first."""
    rows = [row for row in report["tests"] if row["mixed_outcomes"]]
    return sorted(
        rows, key=lambda row: (-row["flips"], -row["fail_rate"], -row["runs"], row["nodeid"])
    )


def format_history(report: dict[str, Any], limit: int, flaky: bool = False) -> str:
    """Show recurring failures and slow tests, or only flaky ones, with their target context."""
    rows = flaky_tests(report) if flaky else report["tests"]
    lines = [
        f"Completed runs: {report['completed_runs']}; ignored manifests: {report['ignored_manifests']}"
    ]
    if flaky and not rows:
        lines.append("No test both passed and failed on the same target.")
    for row in rows[:limit]:
        mixed = " [mixed outcomes]" if row["mixed_outcomes"] and not flaky else ""
        rate = "" if row["fail_rate"] is None else f" ({row['fail_rate']:.0%})"
        lines.append(
            f"{row['nodeid']} [{row['kind']}: {row['device']} / {row['runtime']}] "
            f"{row['failed']}/{row['runs']} failed{rate} {row['outcomes']} "
            f"({row['flips']} flips); "
            f"median {row['median_seconds']}s (setup {row['median_setup_seconds']}s){mixed}"
        )
    return "\n".join(lines)


# Recorded pytest options that reproduce a run; numprocesses is left out so reruns stay serial.
_RERUN_FLAGS = (
    "run_integration",
    "run_diagnostics",
    "run_lifecycle",
    "run_maps_navigation",
    "headless_simulator",
    "restart_simulator",
    "no_reset",
    "skip_simulator_state_reset",
)


def latest_run(root: Path) -> dict[str, Any] | None:
    """Return the most recently finished controller manifest under ``root``."""
    latest: dict[str, Any] | None = None
    for path in root.rglob("run.json"):
        try:
            run = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if (
            isinstance(run, dict)
            and isinstance(run.get("finished_at"), str)
            and run.get("worker") is None
            and isinstance(run.get("results"), list)
            and (latest is None or run["finished_at"] > latest["finished_at"])
        ):
            latest = run
    return latest


def failed_tests(run: dict[str, Any]) -> list[str]:
    """Test IDs that failed in any phase, in the order they ran."""
    failed = [
        result["nodeid"]
        for result in run["results"]
        if isinstance(result, dict) and result.get("outcome") == "failed"
    ]
    return list(dict.fromkeys(failed))


def rerun_options(run: dict[str, Any], skip: AbstractSet[str] = frozenset()) -> list[str]:
    """Rebuild the pytest options that selected the run's device and opt-in suites.

    Args:
        run: A finished run manifest.
        skip: Options the caller sets explicitly; their recorded values are left out.
    """
    recorded = run.get("options") or {}
    options = [
        flag
        for name in _RERUN_FLAGS
        if recorded.get(name) is True and (flag := f"--{name.replace('_', '-')}") not in skip
    ]
    values: list[tuple[str, Any]] = [("--timeout", recorded.get("timeout"))]
    target = run.get("target") or {}
    if target.get("kind") == "simulator":
        values += [
            ("--device-name", target.get("device_name")),
            ("--platform-version", target.get("platform_version")),
        ]
    for option, value in values:
        if option in skip or value is None or isinstance(value, bool):
            continue
        if isinstance(value, int | float) and value > 0:
            options += [option, f"{value:g}"]
        elif isinstance(value, str) and value:
            options += [option, value]
    return options
