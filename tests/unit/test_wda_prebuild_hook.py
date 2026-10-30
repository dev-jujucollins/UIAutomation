"""Simulator runs build WebDriverAgent before tests, outside per-test timeouts."""

import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from uiautomation import pytest_plugin


def _session(*fixturenames: tuple[str, ...], **options) -> SimpleNamespace:
    values = {
        "--run-integration": True,
        "--udid": None,
        "--appium-server": "http://localhost:4723",
        "numprocesses": 0,
        **options,
    }
    config = MagicMock()
    config.getoption.side_effect = lambda name, default=None: values.get(name, default)
    config.option.collectonly = False
    del config.workerinput
    items = [
        SimpleNamespace(fixturenames=names, get_closest_marker=lambda _: None)
        for names in fixturenames
    ]
    return SimpleNamespace(config=config, items=items)


@pytest.mark.parametrize(
    "fixturenames, options, builds",
    [
        ((("driver", "ios_driver"),), {}, True),
        ((("tmp_path",),), {}, False),
        ((("ios_driver",),), {"--udid": "phone"}, False),
        ((("ios_driver",),), {"--appium-server": "http://ci-host:4723"}, False),
        ((("ios_driver",),), {"--run-integration": False}, False),
    ],
)
def test_build_runs_only_for_local_simulator_sessions(fixturenames, options, builds) -> None:
    session = _session(*fixturenames, **options)
    with (
        patch.object(pytest_plugin, "has_prebuilt_wda", return_value=False),
        patch.object(pytest_plugin, "ensure_prebuilt_wda") as build,
    ):
        pytest_plugin.pytest_collection_finish(session)
    assert build.called is builds


def test_current_build_is_not_rebuilt_or_announced() -> None:
    session = _session(("ios_driver",))
    with (
        patch.object(pytest_plugin, "has_prebuilt_wda", return_value=True),
        patch.object(pytest_plugin, "ensure_prebuilt_wda") as build,
    ):
        pytest_plugin.pytest_collection_finish(session)
    build.assert_not_called()
    session.config.pluginmanager.get_plugin.assert_not_called()


def test_build_failure_stops_the_run_with_xcodebuild_output() -> None:
    session = _session(("ios_driver",))
    error = subprocess.CalledProcessError(65, "xcodebuild", stderr="line\n** BUILD FAILED **")
    with (
        patch.object(pytest_plugin, "has_prebuilt_wda", return_value=False),
        patch.object(pytest_plugin, "ensure_prebuilt_wda", side_effect=error),
    ):
        with pytest.raises(pytest.UsageError, match="BUILD FAILED"):
            pytest_plugin.pytest_collection_finish(session)
