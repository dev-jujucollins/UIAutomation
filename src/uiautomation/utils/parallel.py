"""Per-slot resources so several simulator sessions can run at once without sharing."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

# Serial runs keep Appium's defaults (4723, 8100, 9100); slots start above them.
_APPIUM_BASE = 4730
_WDA_BASE = 8110
_MJPEG_BASE = 9110


@dataclass(frozen=True)
class Slot:
    """Ports owned by one parallel session; ``index`` also names its worker simulator."""

    index: int

    @property
    def appium_url(self) -> str:
        return f"http://localhost:{_APPIUM_BASE + self.index}"

    @property
    def wda_port(self) -> int:
        return _WDA_BASE + self.index

    @property
    def mjpeg_port(self) -> int:
        return _MJPEG_BASE + self.index


def worker_slot(config: pytest.Config) -> Slot | None:
    """The xdist worker's slot (``gw2`` -> 2), or None in a serial run or the controller."""
    workerinput = getattr(config, "workerinput", None)
    if not workerinput:
        return None
    return Slot(int(str(workerinput["workerid"]).removeprefix("gw")))
