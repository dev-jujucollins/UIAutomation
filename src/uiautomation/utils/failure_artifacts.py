"""Best-effort failure evidence, independent of screenshot fixtures."""

import json
import re
import shutil
from pathlib import Path
from uuid import uuid4

from appium.webdriver.webdriver import WebDriver


def capture_failure(
    root: Path,
    nodeid: str,
    phase: str,
    driver: WebDriver | None,
    log_path: Path | None,
    failure: str,
) -> Path:
    """Save independent artifacts so one failed capture cannot suppress others."""
    name = re.sub(r"[^\w.-]", "_", nodeid)[-100:]
    destination = root / f"{name}-{phase}-{uuid4().hex[:12]}"
    destination.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    if driver is not None:
        try:
            if not driver.save_screenshot(str(destination / "screen.png")):
                errors.append("Screenshot command returned false")
        except Exception as error:
            errors.append(f"Screenshot: {error}")
        try:
            (destination / "page.xml").write_text(driver.page_source, encoding="utf-8")
        except Exception as error:
            errors.append(f"Page source: {error}")
    else:
        errors.append("No active driver available")
    try:
        if log_path is not None and log_path.is_file():
            shutil.copyfile(log_path, destination / "appium.log")
        else:
            errors.append("Appium log unavailable (external servers require local logs)")
    except Exception as error:
        errors.append(f"Appium log: {error}")
    (destination / "failure.json").write_text(
        json.dumps(
            {"nodeid": nodeid, "phase": phase, "failure": failure, "capture_errors": errors},
            indent=2,
        ),
        encoding="utf-8",
    )
    return destination
