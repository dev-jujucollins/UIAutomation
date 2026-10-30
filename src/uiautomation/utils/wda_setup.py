"""Helpers for building WebDriverAgent for simulator runs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

WDA_PROJECT_PATH = (
    Path.home()
    / ".appium"
    / "node_modules"
    / "appium-xcuitest-driver"
    / "node_modules"
    / "appium-webdriveragent"
    / "WebDriverAgent.xcodeproj"
)
WDA_RUNNER_APP = "WebDriverAgentRunner-Runner.app"
# Written next to the build so a driver or Xcode upgrade triggers a rebuild.
BUILD_STAMP = "uiautomation-wda.json"


def wda_build_identity() -> dict[str, str]:
    """Versions a simulator WDA build depends on: the WDA sources and the selected Xcode."""
    package = json.loads((WDA_PROJECT_PATH.parent / "package.json").read_text())
    xcode = subprocess.run(  # noqa: S603
        ["xcodebuild", "-version"], check=True, capture_output=True, text=True, timeout=30
    ).stdout.strip()
    return {"webdriveragent": str(package["version"]), "xcode": xcode}


def has_prebuilt_wda(derived_data_path: Path) -> bool:
    """Return whether derived data holds a simulator WDA build for the current versions."""
    runner_app = derived_data_path / "Build" / "Products" / "Debug-iphonesimulator" / WDA_RUNNER_APP
    try:
        stamp = json.loads((derived_data_path / BUILD_STAMP).read_text())
    except (OSError, ValueError):
        return False
    return runner_app.exists() and stamp == wda_build_identity()


def ensure_prebuilt_wda(derived_data_path: Path) -> Path:
    """Build WDA for simulator if derived data is missing or was built by other versions."""
    if has_prebuilt_wda(derived_data_path):
        return derived_data_path

    derived_data_path.mkdir(parents=True, exist_ok=True)
    # Remove the stamp first so an interrupted build is never mistaken for a current one.
    (derived_data_path / BUILD_STAMP).unlink(missing_ok=True)
    subprocess.run(  # noqa: S603
        [
            "xcodebuild",
            "-project",
            str(WDA_PROJECT_PATH),
            "-scheme",
            "WebDriverAgentRunner",
            "-sdk",
            "iphonesimulator",
            "-derivedDataPath",
            str(derived_data_path),
            "build-for-testing",
            "GCC_TREAT_WARNINGS_AS_ERRORS=0",
            "COMPILER_INDEX_STORE_ENABLE=NO",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=600,
    )
    (derived_data_path / BUILD_STAMP).write_text(json.dumps(wda_build_identity()))
    return derived_data_path
