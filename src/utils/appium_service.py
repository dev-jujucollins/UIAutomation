"""Helpers for managing local Appium service."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen


def is_local_appium_url(server_url: str) -> bool:
    """Return whether Appium URL points at current machine."""
    parsed = urlparse(server_url)
    return parsed.hostname in {None, "", "localhost", "127.0.0.1"}


def is_appium_server_running(server_url: str, timeout_seconds: float = 1.0) -> bool:
    """Return whether Appium server responds to status request."""
    status_url = f"{server_url.rstrip('/')}/status"
    try:
        with urlopen(status_url, timeout=timeout_seconds) as response:  # noqa: S310
            return response.status == 200
    except (OSError, TimeoutError, URLError, ValueError):
        return False


def wait_for_appium_server(
    server_url: str,
    timeout_seconds: float = 20.0,
    poll_interval_seconds: float = 0.5,
) -> bool:
    """Wait until Appium server responds or timeout expires."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if is_appium_server_running(server_url):
            return True
        time.sleep(poll_interval_seconds)
    return False


@dataclass
class ManagedAppiumService:
    """Local Appium process started by framework."""

    process: subprocess.Popen[str]
    log_path: Path

    def stop(self) -> None:
        """Stop process if still running."""
        if self.process.poll() is not None:
            return

        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)


def start_appium_service(
    server_url: str,
    log_path: Path,
    timeout_seconds: float = 20.0,
) -> ManagedAppiumService:
    """Start local Appium service and wait until ready."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(  # noqa: S603
        ["appium", "--base-path", "/", "--port", str(urlparse(server_url).port or 4723)],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    service = ManagedAppiumService(process=process, log_path=log_path)

    if wait_for_appium_server(server_url, timeout_seconds=timeout_seconds):
        return service

    service.stop()
    raise RuntimeError(f"Appium did not start successfully. See log: {log_path}")
