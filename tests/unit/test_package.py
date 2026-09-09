"""Verify the installed package works independently of the checkout directory."""

import json
import subprocess
import sys
from pathlib import Path


def test_installed_package_imports_outside_checkout(tmp_path: Path) -> None:
    """Exercise every runtime module with cwd and PYTHONPATH excluded from imports."""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            """
import importlib
import importlib.metadata
import json
import pkgutil
import uiautomation

names = [module.name for module in pkgutil.walk_packages(
    uiautomation.__path__, prefix='uiautomation.'
)]
for name in names:
    importlib.import_module(name)
from uiautomation.drivers.ios_driver import IOSDriverConfig
from uiautomation.pages.settings import SettingsHomePage
from uiautomation.utils.app_launcher import AppLauncher
assert isinstance(AppLauncher, type)
assert IOSDriverConfig().platform_name == 'iOS'
assert SettingsHomePage.__module__.startswith('uiautomation.')
assert importlib.metadata.version('uiautomation')
print(json.dumps(names))
""",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    modules = json.loads(result.stdout)
    assert "uiautomation.pages.calendar.new_event" in modules
    assert "uiautomation.utils.failure_artifacts" in modules
    assert all(name.startswith("uiautomation.") for name in modules)


def test_locator_scripts_collect_outside_checkout(tmp_path: Path) -> None:
    """Shared fixtures must load without importing the checkout's tests package."""
    script = Path(__file__).resolve().parents[2] / "scripts" / "inspect_locators.py"
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-m",
            "pytest",
            "--collect-only",
            "--run-integration",
            str(script),
            "-q",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "test_settings_home_top" in result.stdout
    assert "test_calendar_home" in result.stdout


def test_runtime_dependencies_exclude_test_tools() -> None:
    """Installing the framework must not pull in test runners or unused dotenv."""
    from importlib.metadata import requires

    dependencies = requires("uiautomation") or []
    assert not any(
        "pytest" in dependency or "python-dotenv" in dependency for dependency in dependencies
    )
