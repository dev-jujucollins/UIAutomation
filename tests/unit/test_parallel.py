"""Parallel simulator workers own a simulator and ports, derived from their slot."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from uiautomation import pytest_plugin
from uiautomation.drivers.ios_driver import IOSDriver, IOSDriverConfig
from uiautomation.utils import simulator_control as simulators
from uiautomation.utils.parallel import Slot, worker_slot
from uiautomation.utils.simulator_control import SimulatorDevice, ensure_worker_simulator

RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-27-2"
PRO_TYPE = "com.apple.CoreSimulator.SimDeviceType.iPhone-18-Pro"
BASE = SimulatorDevice("iPhone 18 Pro", "base", "27.2", "Booted", True, RUNTIME, PRO_TYPE)


def test_slots_never_share_ports_with_each_other_or_serial_defaults() -> None:
    ports = [(s.appium_url, s.wda_port, s.mjpeg_port) for s in map(Slot, range(8))]
    assert len(set(ports)) == 8
    for url, wda, mjpeg in ports:
        assert not url.endswith(":4723") and wda != 8100 and mjpeg != 9100
    assert Slot(2).appium_url == "http://localhost:4732"


def test_worker_slot_reads_xdist_worker_id() -> None:
    assert worker_slot(SimpleNamespace(workerinput={"workerid": "gw3"})) == Slot(3)
    assert worker_slot(SimpleNamespace()) is None


def test_existing_worker_simulator_is_reused() -> None:
    worker = SimulatorDevice(
        "UIAutomation Worker 1 – iPhone 18 Pro 27.2", "w1", "27.2", "Shutdown", True, RUNTIME
    )
    with (
        patch.object(simulators, "list_available_simulators", return_value=[BASE, worker]),
        patch.object(simulators.subprocess, "run") as run,
    ):
        assert ensure_worker_simulator(BASE, 1) == worker
    run.assert_not_called()


def test_missing_worker_is_created_with_same_model_and_runtime() -> None:
    created = MagicMock(stdout="NEW-UDID\n")
    with (
        patch.object(simulators, "list_available_simulators", return_value=[BASE]),
        patch.object(simulators.subprocess, "run", return_value=created) as run,
    ):
        worker = ensure_worker_simulator(BASE, 0)
    assert run.call_args.args[0] == [
        "xcrun",
        "simctl",
        "create",
        "UIAutomation Worker 0 – iPhone 18 Pro 27.2",
        PRO_TYPE,
        RUNTIME,
    ]
    assert (worker.udid, worker.platform_version) == ("NEW-UDID", "27.2")


def test_workers_for_other_models_or_runtimes_are_distinct() -> None:
    duo = SimulatorDevice("iPhone Duo", "d", "27.2", "Shutdown", True, RUNTIME, "duo-type")
    names = {simulators.worker_simulator_name(device, 0) for device in (BASE, duo)}
    assert len(names) == 2


def test_default_target_never_picks_a_worker() -> None:
    worker = SimulatorDevice("UIAutomation Worker 0 – Custom 28.0", "w", "28.0", "Booted", True)
    custom = SimulatorDevice("Custom Phone", "c", "27.0", "Shutdown", True)
    assert simulators.select_simulator([worker, custom])[0] == custom
    assert simulators.select_simulator([worker, custom], worker.name)[0] == worker


def test_driver_sends_slot_ports_only_when_set() -> None:
    serial = IOSDriver(IOSDriverConfig())._build_options().to_capabilities()
    assert "appium:wdaLocalPort" not in serial
    parallel = (
        IOSDriver(IOSDriverConfig(wda_local_port=8112, mjpeg_server_port=9112))
        ._build_options()
        .to_capabilities()
    )
    assert (parallel["appium:wdaLocalPort"], parallel["appium:mjpegServerPort"]) == (8112, 9112)


@pytest.mark.parametrize("workerinput", [None, {"workerid": "gw2"}])
def test_driver_config_gives_each_worker_its_own_device_and_ports(tmp_path, workerinput) -> None:
    options = {
        "--udid": None,
        "--team-id": None,
        "--device-name": None,
        "--platform-version": None,
        "--appium-server": "http://localhost:4723",
        "--run-integration": False,
    }
    config = MagicMock()
    config.getoption.side_effect = lambda name, default=None: options.get(name, False)
    config.stash = {pytest_plugin.RUN_DIRECTORY: tmp_path}
    if workerinput is None:
        del config.workerinput
    else:
        config.workerinput = workerinput
    worker = SimulatorDevice(
        "UIAutomation Worker 2 – iPhone 18 Pro 27.2", "w2", "27.2", "Shutdown", True, RUNTIME
    )
    with (
        patch.object(pytest_plugin, "get_preferred_simulator", return_value=BASE),
        patch.object(pytest_plugin, "ensure_worker_simulator", return_value=worker) as ensure,
    ):
        result = pytest_plugin.driver_config.__wrapped__(SimpleNamespace(config=config))
    if workerinput is None:
        ensure.assert_not_called()
        assert (result.device_name, result.appium_server_url) == (
            "iPhone 18 Pro",
            "http://localhost:4723",
        )
        assert result.wda_local_port is None
    else:
        ensure.assert_called_once_with(BASE, 2)
        assert (result.device_name, result.appium_server_url, result.wda_local_port) == (
            worker.name,
            Slot(2).appium_url,
            Slot(2).wda_port,
        )


def test_worker_that_cannot_boot_is_recreated() -> None:
    """A worker left half-booted by an interrupted run is disposable: delete and recreate."""
    broken = SimulatorDevice("w", "old", "27.2", "Booted", True, RUNTIME, PRO_TYPE)
    fresh = SimulatorDevice("w", "new", "27.2", "Shutdown", True, RUNTIME, PRO_TYPE)
    boots: list[str] = []

    def boot(udid: str) -> None:
        boots.append(udid)
        if udid == "old":
            raise simulators.subprocess.TimeoutExpired("bootstatus", 120)

    with (
        patch.object(simulators, "ensure_worker_simulator", side_effect=[broken, fresh]),
        patch.object(simulators, "boot_simulator", side_effect=boot),
        patch.object(simulators, "stop_stray_wda"),
        patch.object(simulators.subprocess, "run") as run,
    ):
        assert simulators.boot_worker_simulator(BASE, 0) == fresh
    assert boots == ["old", "new"]
    assert ["xcrun", "simctl", "delete", "old"] in [call.args[0] for call in run.call_args_list]


def test_stray_wda_is_matched_by_device_udid_only() -> None:
    with patch.object(simulators.subprocess, "run") as run:
        simulators.stop_stray_wda("ABC-123")
    assert run.call_args.args[0] == ["pkill", "-f", "xcodebuild.*ABC-123"]
    assert run.call_args.kwargs["check"] is False


def test_slot_build_is_a_copy_on_write_clone_refreshed_when_stale(tmp_path) -> None:
    from uiautomation.utils import wda_setup

    source = tmp_path / "wda"
    with (
        patch.object(wda_setup, "has_prebuilt_wda", return_value=False),
        patch.object(wda_setup.subprocess, "run") as run,
    ):
        target = wda_setup.slot_wda_build(source, 3)
    assert target == tmp_path / "wda-slot3"
    assert run.call_args.args[0] == ["cp", "-cR", str(source), str(target)]
    with (
        patch.object(wda_setup, "has_prebuilt_wda", return_value=True),
        patch.object(wda_setup.subprocess, "run") as run,
    ):
        wda_setup.slot_wda_build(source, 3)
    run.assert_not_called()


@pytest.mark.parametrize("skip_reset", [False, True])
def test_worker_prep_boots_and_resets_under_shared_lock(tmp_path, skip_reset: bool) -> None:
    options = {
        "--device-name": None,
        "--platform-version": None,
        "--skip-simulator-state-reset": skip_reset,
        "--no-reset": False,
    }
    config = MagicMock()
    config.getoption.side_effect = lambda name, default=None: options.get(name, default)
    config.workerinput = {"workerid": "gw1"}
    events: list[str] = []
    lock = MagicMock()
    lock.__enter__.side_effect = lambda: events.append("lock")
    lock.__exit__.side_effect = lambda *_: events.append("unlock")
    worker = SimulatorDevice("w1", "w1", "27.2", "Booted", True, RUNTIME, PRO_TYPE)
    with (
        patch.object(pytest_plugin, "get_preferred_simulator", return_value=BASE),
        patch.object(pytest_plugin, "_exclusive", return_value=lock),
        patch.object(
            pytest_plugin,
            "boot_worker_simulator",
            side_effect=lambda *_: events.append("boot") or worker,
        ),
        patch.object(
            pytest_plugin,
            "reset_simulator_app_state",
            side_effect=lambda udid: events.append(f"reset {udid}"),
        ),
        patch.object(pytest_plugin, "slot_wda_build", side_effect=lambda *_: events.append("wda")),
    ):
        pytest_plugin._prepare_worker_simulator(config)
    expected = ["lock", "boot"] + ([] if skip_reset else ["reset w1"]) + ["unlock", "wda"]
    assert events == expected


def test_worker_sessions_skip_the_reset_done_during_collection(tmp_path) -> None:
    options = {"--appium-server": "http://localhost:4723"}
    config = MagicMock()
    config.getoption.side_effect = lambda name, default=None: options.get(name)
    config.stash = {pytest_plugin.RUN_DIRECTORY: tmp_path}
    config.workerinput = {"workerid": "gw0"}
    worker = SimulatorDevice("w0", "w0", "27.2", "Booted", True, RUNTIME, PRO_TYPE)
    with (
        patch.object(pytest_plugin, "get_preferred_simulator", return_value=BASE),
        patch.object(pytest_plugin, "ensure_worker_simulator", return_value=worker),
    ):
        result = pytest_plugin.driver_config.__wrapped__(SimpleNamespace(config=config))
    assert result.reset_simulator_state is False
    assert result.derived_data_path.endswith("wda-derived-data-slot0")
