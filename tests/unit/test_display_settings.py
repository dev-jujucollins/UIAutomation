"""Runs can switch the simulator to dark mode or a large text size, and restore it."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from uiautomation import pytest_plugin
from uiautomation.utils import simulator_control as simulators
from uiautomation.utils.run_history import rerun_options


def test_ui_settings_use_simctl_ui() -> None:
    with patch.object(simulators.subprocess, "run") as run:
        run.return_value.stdout = "light\n"
        assert simulators.get_ui_setting("U", "appearance") == "light"
        simulators.set_ui_setting("U", "content_size", "extra-large")
    assert run.call_args_list[0].args[0] == ["xcrun", "simctl", "ui", "U", "appearance"]
    assert run.call_args_list[1].args[0] == [
        "xcrun",
        "simctl",
        "ui",
        "U",
        "content_size",
        "extra-large",
    ]


def _request(**options: object) -> SimpleNamespace:
    values = {"--udid": None, "--appearance": None, "--content-size": None, **options}
    config = MagicMock()
    config.getoption.side_effect = lambda name, default=None: values.get(name, default)
    config.stash = {}
    del config.workerinput  # a serial run, not an xdist worker
    return SimpleNamespace(config=config)


@pytest.mark.parametrize("fail", [False, True])
def test_session_applies_then_restores_display_settings(fail: bool) -> None:
    """Originals come back even when the session ends with an error."""
    current = {"appearance": "light", "content_size": "large"}
    calls: list[tuple[str, str]] = []

    def set_setting(udid: str, setting: str, value: str) -> None:
        calls.append((setting, value))
        current[setting] = value

    driver_config = SimpleNamespace(udid="SIM")
    with (
        patch.object(pytest_plugin, "IOSDriver") as driver_type,
        patch.object(pytest_plugin, "get_ui_setting", side_effect=lambda _, s: current[s]),
        patch.object(pytest_plugin, "set_ui_setting", side_effect=set_setting),
    ):
        fixture = pytest_plugin.ios_driver.__wrapped__(
            _request(**{"--appearance": "dark", "--content-size": "accessibility-large"}),
            driver_config,
        )
        next(fixture)
        assert current == {"appearance": "dark", "content_size": "accessibility-large"}
        if fail:
            with pytest.raises(RuntimeError):
                fixture.throw(RuntimeError("test failed"))
        else:
            with pytest.raises(StopIteration):
                next(fixture)
    assert current == {"appearance": "light", "content_size": "large"}
    driver_type.return_value.quit.assert_called_once()


def test_session_without_display_options_changes_nothing() -> None:
    with (
        patch.object(pytest_plugin, "IOSDriver"),
        patch.object(pytest_plugin, "set_ui_setting") as set_setting,
    ):
        fixture = pytest_plugin.ios_driver.__wrapped__(_request(), SimpleNamespace(udid="SIM"))
        next(fixture)
        with pytest.raises(StopIteration):
            next(fixture)
    set_setting.assert_not_called()


def test_rerun_repeats_display_settings() -> None:
    run = {
        "options": {"appearance": "dark", "content_size": "accessibility-large"},
        "target": {"kind": "simulator"},
    }
    options = rerun_options(run)
    assert options == ["--appearance", "dark", "--content-size", "accessibility-large"]
