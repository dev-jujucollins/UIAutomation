"""Tests for pytest support."""

import json
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def harness(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> pytest.Pytester:
    """Run real pytest hooks in a disposable project with no real device."""
    monkeypatch.setenv("PYTHONPATH", str(ROOT))
    pytester.makeconftest((ROOT / "conftest.py").read_text())
    pytester.makeini(
        "[pytest]\nmarkers =\n unit\n integration\n diagnostic\n real_device\n journey\n"
    )
    return pytester


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
def test_hook_captures_each_failure_phase_without_screenshot_fixture(harness, phase) -> None:
    """Evidence must be collected for all phases without opt-in fixtures."""
    harness.makepyfile(f"""
import pytest
from pathlib import Path
class Driver:
    page_source = "<Application/>"
    def save_screenshot(self, path):
        Path(path).write_bytes(b"fake screenshot")
        return True
@pytest.fixture
def driver():
    return Driver()
@pytest.fixture
def prepared(driver):
    if {phase!r} == "setup":
        raise RuntimeError("setup failed")
    yield
    if {phase!r} == "teardown":
        raise RuntimeError("teardown failed")
def test_sample(prepared):
    if {phase!r} == "call":
        raise RuntimeError("call failed")
""")
    result = harness.runpytest_subprocess("-q")
    assert result.ret == 1
    artifacts = list(harness.path.glob("artifacts/*/*/failure.json"))
    assert len(artifacts) == 1
    assert json.loads(artifacts[0].read_text())["phase"] == phase
    assert artifacts[0].with_name("screen.png").exists()
    assert artifacts[0].with_name("page.xml").exists()


def test_device_tests_are_opt_in_and_parallel_device_runs_rejected(harness) -> None:
    """Policy must take effect before any device fixture can run."""
    harness.makepyfile("""
import pytest
def test_unit():
    pass
@pytest.mark.integration
def test_device():
    raise AssertionError("Device test executed")
""")
    harness.runpytest_subprocess("-q").assert_outcomes(passed=1, deselected=1)
    result = harness.runpytest_subprocess("--run-integration", "-n", "2", "-q")
    assert result.ret != 0
    assert "Parallel iOS tests are unsupported" in result.stdout.str() + result.stderr.str()


def test_settings_setup_failure_captures_before_cleanup(harness) -> None:
    """Register finalizers before setup, keeping UI alive for the failure hook."""
    harness.makepyfile("""
import pytest
from pathlib import Path
class Driver:
    page_source = "<Application/>"
    def save_screenshot(self, path):
        assert Path("actions").read_text() == "terminate,launch,"
        Path(path).write_bytes(b"screen")
        return True
class Launcher:
    def record(self, text):
        with Path("actions").open("a") as stream:
            stream.write(text + ",")
    def terminate(self, app): self.record("terminate")
    def launch(self, app): self.record("launch")
@pytest.fixture
def driver(): return Driver()
@pytest.fixture
def app_launcher(): return Launcher()
@pytest.fixture(autouse=True)
def fail_home(monkeypatch):
    from uiautomation.pages.settings import SettingsHomePage
    def fail(self): raise RuntimeError("home missing")
    monkeypatch.setattr(SettingsHomePage, "assert_home_visually_ready", fail)
def test_sample(settings_app): pass
""")
    harness.runpytest_subprocess("-q").assert_outcomes(errors=1)
    assert (harness.path / "actions").read_text() == "terminate,launch,terminate,"
    assert list(harness.path.glob("artifacts/*/*/screen.png"))


def test_wifi_restores_initial_state_after_enable_failure(harness) -> None:
    """Restoration must run even when mutation fails before the test finishes."""
    harness.makepyfile("""
import pytest
from pathlib import Path
class Wifi:
    def is_wifi_enabled(self): return False
    def enable_wifi(self): raise RuntimeError("enable failed")
    def disable_wifi(self): Path("restored").touch()
class Settings:
    def go_to_wifi(self): return Wifi()
@pytest.fixture
def settings_app(): return Settings()
@pytest.fixture
def is_simulator(): return False
def test_sample(restored_wifi): restored_wifi.enable_wifi()
""")
    harness.runpytest_subprocess("-q").assert_outcomes(failed=1)
    assert (harness.path / "restored").exists()


def test_headless_configuration_avoids_simulator_window(harness) -> None:
    """Headless mode should preserve boot/reset behavior while disabling the GUI."""
    harness.makepyfile("""
import pytest
from uiautomation.drivers.ios_driver import IOSDriver
from uiautomation.utils.simulator_control import SimulatorDevice
@pytest.fixture(scope="session", autouse=True)
def available():
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("uiautomation.utils.simulator_control.list_available_simulators", lambda: [
            SimulatorDevice("iPhone", "test-id", "26.4", "Shutdown", True)
        ])
        yield
def test_configuration(driver_config):
    assert driver_config.open_simulator_app is False
    assert driver_config.auto_boot_simulator is True
    assert driver_config.reset_simulator_state is True
    assert IOSDriver(driver_config)._build_options().to_capabilities()["appium:isHeadless"] is True
""")
    harness.runpytest_subprocess(
        "--headless-simulator", "--device-name", "iPhone", "--platform-version", "26.4", "-q"
    ).assert_outcomes(passed=1)


def test_real_device_skip_precedes_fixture_setup(harness) -> None:
    """Unsupported targets must not run any device fixture."""
    harness.makepyfile("""
import pytest
from pathlib import Path
@pytest.fixture
def hardware():
    Path("started").touch()
@pytest.mark.real_device(reason="Radio requires hardware")
def test_radio(hardware): pass
""")
    harness.runpytest_subprocess("-q").assert_outcomes(skipped=1)
    assert not (harness.path / "started").exists()
    harness.runpytest_subprocess("--udid", "physical-id", "-q").assert_outcomes(passed=1)
    assert (harness.path / "started").exists()
