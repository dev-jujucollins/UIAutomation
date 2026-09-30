"""Compare completed controller manifests without retrying tests."""

import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


def summarize_history(root: Path) -> dict[str, Any]:
    """Group results by test and target; mixed outcomes are candidates, not proof of flakiness."""
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
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
            for nodeid, test in tests.items():
                if test["outcome"] is not None:
                    groups[(*identity, nodeid)].append(test)
            seen.add(run_id)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            ignored += 1
    rows = []
    for (kind, device, runtime, nodeid), runs in groups.items():
        passed = sum(run["outcome"] == "passed" for run in runs)
        failed = sum(run["outcome"] == "failed" for run in runs)
        rows.append(
            {
                "nodeid": nodeid,
                "kind": kind,
                "device": device,
                "runtime": runtime,
                "runs": len(runs),
                "passed": passed,
                "failed": failed,
                "mixed_outcomes": bool(passed and failed),
                "median_seconds": round(median(run["total"] for run in runs), 3),
                "median_setup_seconds": round(median(run["setup"] for run in runs), 3),
            }
        )
    rows.sort(key=lambda row: (-row["failed"], -row["median_seconds"], row["nodeid"]))
    return {"completed_runs": len(seen), "ignored_manifests": ignored, "tests": rows}


def format_history(report: dict[str, Any], limit: int) -> str:
    """Show recurring failures and slow tests with their target context."""
    lines = [
        f"Completed runs: {report['completed_runs']}; ignored manifests: {report['ignored_manifests']}"
    ]
    for row in report["tests"][:limit]:
        mixed = " [mixed outcomes]" if row["mixed_outcomes"] else ""
        lines.append(
            f"{row['nodeid']} [{row['kind']}: {row['device']} / {row['runtime']}] "
            f"{row['failed']}/{row['runs']} failed; median {row['median_seconds']}s "
            f"(setup {row['median_setup_seconds']}s){mixed}"
        )
    return "\n".join(lines)
