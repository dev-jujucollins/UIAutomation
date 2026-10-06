"""Calendar draft finalizers protect later tests after partial failures."""

from pathlib import Path

import pytest

pytest_plugins = ["pytester"]
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("fail_during_open", [False, True])
def test_calendar_draft_is_discarded_after_failure(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch, fail_during_open: bool
) -> None:
    monkeypatch.setenv("PYTHONPATH", str(ROOT))
    pytester.makeconftest((ROOT / "conftest.py").read_text())
    pytester.makepyfile(f"""
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from uiautomation.pages.calendar import NewEventPage
@pytest.fixture
def calendar_home(monkeypatch):
    monkeypatch.setattr(NewEventPage, "discard", lambda self: Path("discarded").touch())
    home = MagicMock()
    if {fail_during_open!r}:
        home.tap_add_event.side_effect = RuntimeError("partial editor setup")
    return home

def test_sample(calendar_draft):
    raise AssertionError("test failed while editing")
""")
    result = pytester.runpytest_subprocess("-q")
    assert result.ret == 1
    assert (pytester.path / "discarded").exists()


@pytest.mark.parametrize(
    "enabled, simulator, device_name, expected",
    [
        (False, True, "isolated", "skip"),
        (True, False, "phone", "skip"),
        (True, True, None, "error"),
        (True, True, "isolated", "ok"),
    ],
)
def test_lifecycle_guard_precedes_data_access(
    enabled: bool, simulator: bool, device_name: str | None, expected: str
) -> None:
    from unittest.mock import MagicMock

    from uiautomation import pytest_plugin

    request = MagicMock()
    options = {"--run-lifecycle": enabled, "--device-name": device_name}
    request.config.getoption.side_effect = options.__getitem__
    guard = pytest_plugin.lifecycle_simulator.__wrapped__
    if expected == "skip":
        with pytest.raises(pytest.skip.Exception):
            guard(request, simulator)
    elif expected == "error":
        with pytest.raises(pytest.UsageError, match="--device-name"):
            guard(request, simulator)
    else:
        guard(request, simulator)
    request.getfixturevalue.assert_not_called()
