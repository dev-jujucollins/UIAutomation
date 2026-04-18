"""Helpers for building WebDriverAgent for simulator runs."""

from __future__ import annotations

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


def has_prebuilt_wda(derived_data_path: Path) -> bool:
    """Return whether derived data already contains simulator WDA build."""
    runner_app = derived_data_path / "Build" / "Products" / "Debug-iphonesimulator" / WDA_RUNNER_APP
    return runner_app.exists()


def ensure_prebuilt_wda(derived_data_path: Path) -> Path:
    """Build WDA for simulator if derived data is missing."""
    if has_prebuilt_wda(derived_data_path):
        return derived_data_path

    derived_data_path.mkdir(parents=True, exist_ok=True)
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
    )
    return derived_data_path
