from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .appium_service import (
    ManagedAppiumService,
    is_appium_server_running,
    is_local_appium_url,
    start_appium_service,
    wait_for_appium_server,
)
from .simulator_control import (
    SimulatorDevice,
    boot_simulator,
    find_simulator,
    get_preferred_simulator,
    list_available_simulators,
    open_simulator_app,
)
from .wda_setup import ensure_prebuilt_wda, has_prebuilt_wda

if TYPE_CHECKING:
    from .app_launcher import AppLauncher
else:
    AppLauncher = Any


def __getattr__(name: str):
    """Lazily expose utilities that would otherwise create import cycles."""
    if name == "AppLauncher":
        from .app_launcher import AppLauncher

        return AppLauncher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AppLauncher",
    "ManagedAppiumService",
    "SimulatorDevice",
    "boot_simulator",
    "find_simulator",
    "get_preferred_simulator",
    "has_prebuilt_wda",
    "is_appium_server_running",
    "is_local_appium_url",
    "list_available_simulators",
    "open_simulator_app",
    "start_appium_service",
    "wait_for_appium_server",
    "ensure_prebuilt_wda",
]
