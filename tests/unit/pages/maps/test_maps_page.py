"""Maps assertions, permission decisions, and fixture ownership contracts."""

from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

import conftest
from uiautomation.pages.maps import MapsPage


@pytest.mark.parametrize(
    "label,valid",
    [
        ("4 min, 8:42 ETA · 2.7 mi, Fastest", True),
        ("1 hr 4 min, 9:43 ETA · 2.8 mi, 300 feet climb", True),
        ("15 min, 900 m", True),
        ("No routes available", False),
        ("4 min, no distance", False),
        ("2.7 mi", False),
        ("0 min, 2 mi", False),
        ("4 min, 0 mi", False),
        ("Create a Custom Route", False),
    ],
)
def test_route_metrics_reject_errors_and_missing_values(label: str, valid: bool) -> None:
    assert MapsPage.valid_summary(label) is valid


@pytest.mark.parametrize("origin", [(91, 0), (0, -181), (float("nan"), 0)])
def test_invalid_coordinates_never_open_maps(origin: tuple[float, float]) -> None:
    page = MapsPage(MagicMock())
    with pytest.raises(ValueError):
        page.preview_route(origin, (37.8, -122.4))
    page.driver.execute_script.assert_not_called()


def test_route_link_has_explicit_endpoints_and_driving_mode() -> None:
    page = MapsPage(MagicMock())
    page.ready_control = MagicMock()
    page.route_summary = MagicMock()
    page.preview_route((37.8029, -122.4484), (37.8199, -122.4783))
    command, options = page.driver.execute_script.call_args.args
    assert command == "mobile: deepLink"
    assert options["bundleId"] == "com.apple.Maps"
    assert parse_qs(urlparse(options["url"]).query) == {
        "saddr": ["37.8029,-122.4484"],
        "daddr": ["37.8199,-122.4783"],
        "dirflg": ["d"],
    }


@pytest.mark.parametrize(
    "permission,button", [("allow", "Allow While Using App"), ("deny", "Don’t Allow")]
)
def test_location_decision_uses_matching_prompt(permission: str, button: str) -> None:
    page = MapsPage(MagicMock())
    alert = MagicMock()
    alert.get_attribute.return_value = "Allow “Maps” to use your location?"
    page.driver.find_elements.return_value = [alert]
    assert page.dismiss_known_onboarding(permission)
    alert.find_element.assert_called_once_with(page.By.ACCESSIBILITY_ID, button)


def test_unexpected_alert_fails_without_accepting() -> None:
    page = MapsPage(MagicMock())
    alert = MagicMock()
    alert.get_attribute.return_value = "Unexpected account prompt"
    page.driver.find_elements.return_value = [alert]
    with pytest.raises(AssertionError, match="Unexpected Maps alert"):
        page.dismiss_known_onboarding()
    alert.find_element.assert_not_called()


def test_visibility_skips_stale_and_hidden_controls() -> None:
    page = MapsPage(MagicMock())
    stale, hidden, visible = MagicMock(), MagicMock(), MagicMock()
    stale.is_displayed.side_effect = StaleElementReferenceException()
    hidden.is_displayed.return_value = False
    page.driver.find_elements.return_value = [stale, hidden, visible]
    assert page._visible(page.SEARCH) is visible


def test_wrong_place_cannot_pass_as_expected_landmark() -> None:
    page = MapsPage(MagicMock())
    page.ready_control = MagicMock()
    page.ready_control.return_value.get_attribute.return_value = "Wrong bridge, Landmark"
    with pytest.raises(AssertionError):
        page.assert_place("Golden Gate Bridge")


def test_failed_mode_selection_cannot_pass_with_old_summary() -> None:
    page = MapsPage(MagicMock())
    page.DEFAULT_TIMEOUT = 0
    page.ready_control = MagicMock()
    page.find_element = MagicMock()
    page.find_element.return_value.get_attribute.return_value = None
    page.route_summary = MagicMock()
    with pytest.raises(TimeoutException):
        page.select_mode("walk")
    page.route_summary.assert_not_called()


def test_unavailable_route_does_not_pass_as_valid_preview() -> None:
    page = MapsPage(MagicMock())
    page.NETWORK_TIMEOUT = 0
    page.dismiss_known_onboarding = MagicMock()
    page._visible = MagicMock()
    page._visible.return_value.get_attribute.return_value = "Directions Not Available"
    with pytest.raises(TimeoutException):
        page.route_summary()


def test_cleanup_has_bounded_attempts() -> None:
    page = MapsPage(MagicMock())
    page.dismiss_known_onboarding = MagicMock(return_value=False)
    close = MagicMock()
    page._visible = MagicMock(return_value=close)
    with pytest.raises(AssertionError, match="six"):
        page.close_to_home()
    assert close.click.call_count == 6


def test_maps_requires_dedicated_simulator_before_driver_setup() -> None:
    request = MagicMock()
    request.config.getoption.return_value = "Personal iPhone"
    with pytest.raises(pytest.UsageError, match="UIAutomation Maps"):
        next(conftest.maps_home.__wrapped__(request, True))
    request.getfixturevalue.assert_not_called()


def test_maps_skips_physical_device_before_driver_setup() -> None:
    request = MagicMock()
    with pytest.raises(pytest.skip.Exception):
        next(conftest.maps_home.__wrapped__(request, False))
    request.getfixturevalue.assert_not_called()


def test_permission_cleanup_registered_before_launch_failure() -> None:
    request, driver, launcher = MagicMock(), MagicMock(), MagicMock()
    request.config.getoption.return_value = "UIAutomation Maps"
    request.getfixturevalue.side_effect = [driver, launcher]
    driver.capabilities = {"udid": "test-simulator"}
    launcher.launch.side_effect = RuntimeError("launch failed")
    with patch("conftest.subprocess.run") as run:
        with pytest.raises(RuntimeError, match="launch failed"):
            next(conftest.maps_home.__wrapped__(request, True))
        for finalizer in reversed(request.addfinalizer.call_args_list):
            finalizer.args[0]()
    assert run.call_count == 2
    assert run.call_args.args[0] == [
        "xcrun",
        "simctl",
        "privacy",
        "test-simulator",
        "reset",
        "location",
        "com.apple.Maps",
    ]
    assert launcher.terminate.call_count == 2
