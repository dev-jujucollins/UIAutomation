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


@pytest.mark.parametrize("permission,button", [("allow", "Allow"), ("deny", "Don’t Allow")])
def test_widgets_location_decision_uses_matching_prompt(permission: str, button: str) -> None:
    page = MapsPage(MagicMock())
    alert = MagicMock()
    alert.get_attribute.return_value = "Allow widgets from “Maps” to use your location?"
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


def test_route_options_tip_is_dismissed_only_when_present() -> None:
    page = MapsPage(MagicMock())
    page.driver.find_elements.return_value = []
    close = MagicMock()
    page._visible = MagicMock(
        side_effect=lambda locator: close
        if locator[1] in ("Choose Your Route Options", "xmark.circle.fill")
        else None
    )
    assert page.dismiss_known_onboarding()
    close.click.assert_called_once()


def test_eta_notifications_sheet_uses_current_dismiss_button() -> None:
    page = MapsPage(MagicMock())
    page.driver.find_elements.return_value = []
    dismiss = MagicMock()
    page._visible = MagicMock(
        side_effect=lambda locator: dismiss
        if locator[1] in ("Get Notified When Friends Share Their ETAs", "Dismiss")
        else None
    )
    assert page.dismiss_known_onboarding()
    dismiss.click.assert_called_once()


def test_recenter_requires_my_location_and_apple_park_landmark() -> None:
    page = MapsPage(MagicMock())
    page.ready_control = MagicMock()
    page.recenter_at_apple_park()
    assert [call.args for call in page.ready_control.call_args_list] == [
        (page.RECENTER, "allow"),
        (page.MY_LOCATION, "allow"),
        (page.APPLE_PARK_NEARBY, "allow"),
    ]
    page.ready_control.return_value.click.assert_called_once()


def test_search_uses_keyboard_submit_when_visible() -> None:
    page = MapsPage(MagicMock())
    page.edit_search = MagicMock()
    page.assert_place = MagicMock()
    page.dismiss_known_onboarding = MagicMock(return_value=False)
    submit = MagicMock()
    page._visible = MagicMock(return_value=submit)
    page.search_place("Golden Gate Bridge San Francisco", "Golden Gate Bridge")
    submit.click.assert_called_once()
    page.driver.find_elements.assert_not_called()


def test_search_uses_exact_title_suggestion_when_keyboard_hidden() -> None:
    page = MapsPage(MagicMock())
    page.edit_search = MagicMock()
    page.assert_place = MagicMock()
    page.dismiss_known_onboarding = MagicMock(return_value=False)
    page._visible = MagicMock(return_value=None)
    stale, unrelated, expected = MagicMock(), MagicMock(), MagicMock()
    stale.is_displayed.side_effect = StaleElementReferenceException()
    unrelated.get_attribute.return_value = "Golden Gate Bridge Bike Rentals, San Francisco"
    expected.get_attribute.return_value = "Golden Gate Bridge, San Francisco, CA"
    page.driver.find_elements.return_value = [stale, unrelated, expected]
    page.search_place("Golden Gate Bridge San Francisco", "Golden Gate Bridge")
    stale.click.assert_not_called()
    unrelated.click.assert_not_called()
    expected.click.assert_called_once()


def test_search_rejects_unrelated_suggestions_when_keyboard_hidden() -> None:
    page = MapsPage(MagicMock())
    page.NETWORK_TIMEOUT = 0
    page.edit_search = MagicMock()
    page.assert_place = MagicMock()
    page.dismiss_known_onboarding = MagicMock(return_value=False)
    page._visible = MagicMock(return_value=None)
    unrelated = MagicMock()
    unrelated.get_attribute.return_value = "Golden Gate Bridge Bike Rentals, San Francisco"
    page.driver.find_elements.return_value = [unrelated]
    with pytest.raises(TimeoutException):
        page.search_place("Golden Gate Bridge San Francisco", "Golden Gate Bridge")
    page.assert_place.assert_not_called()


@pytest.mark.parametrize("locator_name", ["ROUTE_SUMMARY", "ROUTE_SUMMARY_LEGACY"])
def test_route_summary_accepts_current_and_legacy_card_shapes(locator_name: str) -> None:
    page = MapsPage(MagicMock())
    page.dismiss_known_onboarding = MagicMock(return_value=False)
    summary = MagicMock()
    summary.get_attribute.return_value = "1 hr 9 min · 48 mi"
    page._visible = MagicMock(
        side_effect=lambda locator: summary if locator == getattr(page, locator_name) else None
    )
    assert page.route_summary() == "1 hr 9 min · 48 mi"


def test_navigation_requires_destination_and_maneuver() -> None:
    page = MapsPage(MagicMock())
    controls = {
        locator: MagicMock()
        for locator in (page.STEPS_BUTTON, page.NAV_TRAY, page.NAV_DESTINATION, page.NAV_MANEUVER)
    }
    controls[page.NAV_DESTINATION].get_attribute.return_value = "To Golden Gate Bridge, 1 hr 10 min"
    controls[page.NAV_MANEUVER].get_attribute.return_value = "80 ft, Turn right"
    page.ready_control = MagicMock(side_effect=controls.__getitem__)
    assert page.start_navigation("Golden Gate Bridge") == "80 ft, Turn right"
    controls[page.STEPS_BUTTON].click.assert_called_once()
    page.ready_control.assert_any_call(page.NAV_TRAY)


def test_navigation_rejects_wrong_destination() -> None:
    page = MapsPage(MagicMock())
    page.ready_control = MagicMock()
    page.ready_control.return_value.get_attribute.return_value = "To Another Place, 10 min"
    with pytest.raises(AssertionError):
        page.start_navigation("Golden Gate Bridge")


def test_end_navigation_uses_owned_route_control() -> None:
    page = MapsPage(MagicMock())
    page._visible = MagicMock(return_value=MagicMock())
    page.ready_control = MagicMock()
    page.end_navigation()
    assert [call.args[0] for call in page.ready_control.call_args_list] == [
        page.NAV_GRABBER,
        page.END_ROUTE,
        page.PLACE,
    ]


def test_end_navigation_does_nothing_without_active_route() -> None:
    page = MapsPage(MagicMock())
    page._visible = MagicMock(return_value=None)
    page.ready_control = MagicMock()
    page.end_navigation()
    page.ready_control.assert_not_called()


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


@pytest.mark.parametrize("device_name", [None, "iPhone 17 Pro", "Custom Simulator"])
@pytest.mark.parametrize("permission", ["deny", "allow"])
def test_maps_uses_apple_park_on_selected_simulator(
    device_name: str | None, permission: str
) -> None:
    request, driver, launcher = MagicMock(), MagicMock(), MagicMock()
    request.config.getoption.return_value = device_name
    request.param = permission
    request.getfixturevalue.side_effect = [driver, launcher]
    driver.capabilities = {"udid": "selected-simulator"}
    with patch("conftest.subprocess.run") as run, patch("conftest.MapsPage") as page_type:
        fixture = conftest.maps_home.__wrapped__(request, True)
        assert next(fixture) is page_type.return_value
        page_type.assert_called_once_with(driver)
        page_type.return_value.wait_until_ready.assert_called_once_with(permission)
        for finalizer in reversed(request.addfinalizer.call_args_list):
            finalizer.args[0]()
        page_type.return_value.dismiss_known_onboarding.assert_called_once_with("deny")
    assert [invocation.args[0] for invocation in run.call_args_list] == [
        [
            "xcrun",
            "simctl",
            "privacy",
            "selected-simulator",
            "reset",
            "location",
            "com.apple.Maps",
        ],
        ["xcrun", "simctl", "location", "selected-simulator", "set", "37.3349,-122.00902"],
        [
            "xcrun",
            "simctl",
            "privacy",
            "selected-simulator",
            "reset",
            "location",
            "com.apple.Maps",
        ],
        ["xcrun", "simctl", "location", "selected-simulator", "clear"],
    ]


def test_maps_skips_physical_device_before_driver_setup() -> None:
    request = MagicMock()
    with pytest.raises(pytest.skip.Exception):
        next(conftest.maps_home.__wrapped__(request, False))
    request.getfixturevalue.assert_not_called()


def test_permission_cleanup_registered_before_launch_failure() -> None:
    request, driver, launcher = MagicMock(), MagicMock(), MagicMock()
    request.getfixturevalue.side_effect = [driver, launcher]
    driver.capabilities = {"udid": "test-simulator"}
    launcher.launch.side_effect = RuntimeError("launch failed")
    with patch("conftest.subprocess.run") as run:
        with pytest.raises(RuntimeError, match="launch failed"):
            next(conftest.maps_home.__wrapped__(request, True))
        for finalizer in reversed(request.addfinalizer.call_args_list):
            finalizer.args[0]()
    assert [call.args[0] for call in run.call_args_list] == [
        ["xcrun", "simctl", "privacy", "test-simulator", "reset", "location", "com.apple.Maps"],
        ["xcrun", "simctl", "location", "test-simulator", "set", "37.3349,-122.00902"],
        ["xcrun", "simctl", "privacy", "test-simulator", "reset", "location", "com.apple.Maps"],
        ["xcrun", "simctl", "location", "test-simulator", "clear"],
    ]
    assert launcher.terminate.call_count == 2


def test_location_cleanup_registered_before_set_failure() -> None:
    request, driver, launcher = MagicMock(), MagicMock(), MagicMock()
    request.getfixturevalue.side_effect = [driver, launcher]
    driver.capabilities = {"udid": "test-simulator"}
    with patch("conftest.subprocess.run") as run:
        run.side_effect = [None, RuntimeError("set failed"), None, None]
        with pytest.raises(RuntimeError, match="set failed"):
            next(conftest.maps_home.__wrapped__(request, True))
        for finalizer in reversed(request.addfinalizer.call_args_list):
            finalizer.args[0]()
    assert run.call_args_list[-1].args[0] == [
        "xcrun",
        "simctl",
        "location",
        "test-simulator",
        "clear",
    ]


@pytest.mark.parametrize("opt_in,is_simulator", [(False, True), (True, False)])
def test_navigation_skips_before_driver_setup(opt_in: bool, is_simulator: bool) -> None:
    request = MagicMock()
    request.config.getoption.return_value = opt_in
    with pytest.raises(pytest.skip.Exception):
        conftest.maps_navigation_guard.__wrapped__(request, is_simulator)
    request.getfixturevalue.assert_not_called()


def test_navigation_requires_explicit_device() -> None:
    request = MagicMock()
    request.config.getoption.side_effect = lambda option: (
        True if option == "--run-maps-navigation" else None
    )
    with pytest.raises(pytest.UsageError, match="--device-name"):
        conftest.maps_navigation_guard.__wrapped__(request, True)


def test_navigation_cleanup_registered_before_recenter_fails() -> None:
    request, page = MagicMock(), MagicMock()
    page.recenter_at_apple_park.side_effect = RuntimeError("recenter failed")
    with pytest.raises(RuntimeError, match="recenter failed"):
        conftest.apple_park_maps.__wrapped__(request, None, page)
    for finalizer in reversed(request.addfinalizer.call_args_list):
        finalizer.args[0]()
    page.end_navigation.assert_called_once()
