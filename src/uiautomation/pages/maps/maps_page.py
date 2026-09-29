"""Maps controls observed on the English iOS 27 simulator."""

from __future__ import annotations

import re
from typing import Literal, cast
from urllib.parse import urlencode

from appium.webdriver.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from ...drivers.ios_driver import SystemApps
from ..base_page import BasePage


class MapsPage(BasePage):
    """Exercise Maps search, route previews, and simulated navigation."""

    SEARCH = (BasePage.By.ACCESSIBILITY_ID, "MapsSearchTextField")
    HOME = (BasePage.By.ACCESSIBILITY_ID, "HomeView")
    PLACE = (BasePage.By.ACCESSIBILITY_ID, "PlaceHeaderView")
    DIRECTIONS = (BasePage.By.ACCESSIBILITY_ID, "ActionRowItemTypeDirections")
    ROUTE = (BasePage.By.ACCESSIBILITY_ID, "IOSRoutePlanningOverview")
    CARD_CLOSE = (BasePage.By.ACCESSIBILITY_ID, "CardButtonTypeClose")
    SEARCH_CLOSE = (BasePage.By.ACCESSIBILITY_ID, "Close")
    SEARCH_SUBMIT = (BasePage.By.ACCESSIBILITY_ID, "Search")
    SEARCH_SUGGESTIONS = (
        BasePage.By.IOS_CLASS_CHAIN,
        '**/XCUIElementTypeButton[`name == "MultiTextView"`]',
    )
    WAYPOINTS = (BasePage.By.ACCESSIBILITY_ID, "WaypointNameText")
    RECENTER = (BasePage.By.ACCESSIBILITY_ID, "UserLocationButton")
    MY_LOCATION = (BasePage.By.ACCESSIBILITY_ID, "My Location")
    APPLE_PARK_NEARBY = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeOther' AND label BEGINSWITH 'Apple Park Visitor Center'",
    )
    ROUTE_SUMMARY = (
        BasePage.By.IOS_CLASS_CHAIN,
        '**/XCUIElementTypeOther[`name == "RoutePlanningCell"`]'
        '/XCUIElementTypeStaticText[`name BEGINSWITH "TitleLabel-SubtitleLabel"`]',
    )
    ROUTE_SUMMARY_LEGACY = (
        BasePage.By.IOS_CLASS_CHAIN,
        '**/XCUIElementTypeOther[`name == "RoutePlanningCell"`]'
        '/XCUIElementTypeOther[`name BEGINSWITH "TitleLabel-SubtitleLabel"`]',
    )
    STEPS_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "StepsLabel-StepsLabel")
    NAV_TRAY = (BasePage.By.ACCESSIBILITY_ID, "NavTray")
    NAV_MANEUVER = (BasePage.By.ACCESSIBILITY_ID, "NavManeuverSignView")
    NAV_DESTINATION = (BasePage.By.ACCESSIBILITY_ID, "DefaultLabel")
    NAV_GRABBER = (BasePage.By.ACCESSIBILITY_ID, "Card grabber")
    END_ROUTE = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND label == 'End Route'",
    )
    MODES = {"drive": "DriveButton", "walk": "WalkButton"}
    NETWORK_TIMEOUT = 45

    def _visible(self, locator: tuple[str, str]) -> WebElement | None:
        """Find a visible match, ignoring stale controls during transitions."""
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return element
            except StaleElementReferenceException:
                continue
        return None

    def dismiss_known_onboarding(self, permission: Literal["allow", "deny"] = "deny") -> bool:
        """Dismiss only recognized Maps prompts; leave unexpected alerts to fail."""
        alerts = self.driver.find_elements(self.By.CLASS_NAME, "XCUIElementTypeAlert")
        for alert in alerts:
            if not alert.is_displayed():
                continue
            title = alert.get_attribute("name") or ""
            if title == "Allow “Maps” to use your location?":
                button = "Allow While Using App" if permission == "allow" else "Don’t Allow"
            elif title == "Allow widgets from “Maps” to use your location?":
                button = "Allow" if permission == "allow" else "Don’t Allow"
            elif title == "“Maps” Would Like to Send You Notifications":
                button = "Don’t Allow"
            elif title == "Getting There Safely":
                button = "OK"
            else:
                raise AssertionError(f"Unexpected Maps alert: {title}")
            alert.find_element(self.By.ACCESSIBILITY_ID, button).click()
            return True
        for heading, buttons in (
            ("Get Notified When Friends Share Their ETAs", ("Dismiss", "Not Now")),
            ("EnrichmentWarmingSheetGraphic_Light", ("Continue",)),
            ("Choose Your Route Options", ("xmark.circle.fill",)),
        ):
            if self._visible((self.By.ACCESSIBILITY_ID, heading)):
                for button in buttons:
                    control = self._visible((self.By.ACCESSIBILITY_ID, button))
                    if control:
                        control.click()
                        return True
                raise AssertionError(f"Known Maps sheet has no dismiss control: {heading}")
        return False

    def ready_control(
        self, locator: tuple[str, str], permission: Literal["allow", "deny"] = "deny"
    ) -> WebElement:
        """Wait through known onboarding and asynchronous service responses."""

        def ready(_: object) -> WebElement | None:
            if self.dismiss_known_onboarding(permission):
                return None
            return self._visible(locator)

        return cast(WebElement, self._get_wait(self.NETWORK_TIMEOUT).until(ready))

    def wait_until_ready(self, permission: Literal["allow", "deny"] = "deny") -> None:
        """Require a home card and usable search field."""
        self.ready_control(self.HOME, permission)
        self.ready_control(self.SEARCH, permission)

    def recenter_at_apple_park(self) -> None:
        """Center the map on simulated location and require nearby Apple Park."""
        self.ready_control(self.RECENTER, "allow").click()
        self.ready_control(self.MY_LOCATION, "allow")
        self.ready_control(self.APPLE_PARK_NEARBY, "allow")

    def query(self) -> str:
        """Read query, normalizing UIKit placeholder values."""
        field = self.find_element(self.SEARCH)
        value = field.get_attribute("value")
        if value is None or value == field.get_attribute("placeholderValue"):
            return ""
        if not isinstance(value, str):
            raise AssertionError("Maps query returned a non-text value")
        return value

    def edit_search(self, query: str) -> None:
        """Replace query without selecting a suggestion or submitting it."""
        field = self.ready_control(self.SEARCH)
        field.click()
        field.clear()
        if query:
            field.send_keys(query)
        self._get_wait(None).until(lambda _: self.query() == query)

    def search_place(self, query: str, expected_name: str) -> None:
        """Submit a specific query and require its expected place card."""
        self.edit_search(query)

        def submit(_: object) -> WebElement | None:
            if self.dismiss_known_onboarding():
                return None
            keyboard_search = self._visible(self.SEARCH_SUBMIT)
            if keyboard_search:
                return keyboard_search
            for suggestion in self.driver.find_elements(*self.SEARCH_SUGGESTIONS):
                try:
                    if not suggestion.is_displayed():
                        continue
                    label = suggestion.get_attribute("label")
                except StaleElementReferenceException:
                    continue
                if (
                    isinstance(label, str)
                    and label.startswith(f"{expected_name},")
                    and "Search Nearby" not in label
                ):
                    return suggestion
            return None

        cast(WebElement, self._get_wait(self.NETWORK_TIMEOUT).until(submit)).click()
        self.assert_place(expected_name)

    def assert_place(self, expected_name: str) -> None:
        """Verify place identity and available Directions action."""
        header = self.ready_control(self.PLACE)
        label = header.get_attribute("label")
        assert isinstance(label, str) and label.split(",", 1)[0] == expected_name, label
        self.ready_control(self.DIRECTIONS)

    def open_directions(self) -> None:
        """Open route planning from the current place card."""
        self.ready_control(self.DIRECTIONS).click()
        self.ready_control(self.ROUTE)

    def preview_route(self, origin: tuple[float, float], destination: tuple[float, float]) -> None:
        """Open a driving preview with explicit coordinates via the Maps URL handler."""
        for latitude, longitude in (origin, destination):
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError("Route coordinates out of range")
        params = urlencode(
            {
                "saddr": f"{origin[0]},{origin[1]}",
                "daddr": f"{destination[0]},{destination[1]}",
                "dirflg": "d",
            }
        )
        self.driver.execute_script(
            "mobile: deepLink",
            {"url": f"http://maps.apple.com/?{params}", "bundleId": SystemApps.MAPS.value},
        )
        self.ready_control(self.ROUTE)
        self.route_summary()

    def waypoints(self) -> list[str]:
        """Read ordered endpoint labels, excluding the Add Stop affordance."""
        return [
            str(element.get_attribute("label"))
            for element in self.driver.find_elements(*self.WAYPOINTS)
            if element.is_displayed() and element.get_attribute("label") != "Add Stop"
        ]

    @staticmethod
    def valid_summary(label: str) -> bool:
        """Require positive duration and distance without fixing live ETA values."""
        duration = re.search(r"(\d+(?:\.\d+)?)\s*(?:min|hr|hour|day)\b", label)
        distance = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:mi|km|ft|m)\b", label)
        return bool(
            duration
            and float(duration[1]) > 0
            and distance
            and float(distance[1].replace(",", "")) > 0
        )

    def route_summary(self) -> str:
        """Wait for visible route duration and distance; errors cannot pass as routes."""

        def summary(_: object) -> str | bool:
            self.dismiss_known_onboarding()
            for locator in (self.ROUTE_SUMMARY, self.ROUTE_SUMMARY_LEGACY):
                element = self._visible(locator)
                label = element.get_attribute("label") if element else None
                if isinstance(label, str) and self.valid_summary(label):
                    return label
            return False

        return str(self._get_wait(self.NETWORK_TIMEOUT).until(summary))

    def start_navigation(self, destination: str) -> str:
        """Start simulated guidance and require a maneuver and destination tray."""
        self.ready_control(self.STEPS_BUTTON).click()
        self.ready_control(self.NAV_TRAY)
        tray_label = self.ready_control(self.NAV_DESTINATION).get_attribute("label")
        assert isinstance(tray_label, str) and tray_label.startswith(f"To {destination},"), (
            tray_label
        )
        maneuver = self.ready_control(self.NAV_MANEUVER).get_attribute("label")
        assert isinstance(maneuver, str) and maneuver.strip(), maneuver
        return maneuver

    def end_navigation(self) -> None:
        """End a test-started route through Maps' own End Route control."""
        if not self._visible(self.NAV_TRAY):
            return
        self.ready_control(self.NAV_GRABBER).click()
        self.ready_control(self.END_ROUTE).click()
        self.ready_control(self.PLACE)

    def select_mode(self, mode: Literal["drive", "walk"]) -> str:
        """Switch route mode and require its selected state and valid route data."""
        locator = (self.By.ACCESSIBILITY_ID, self.MODES[mode])
        self.ready_control(locator).click()
        self._get_wait(None).until(
            lambda _: self.find_element(locator).get_attribute("value") == "1"
        )
        return self.route_summary()

    def close_to_home(self) -> None:
        """Dismiss owned route/place/search sheets with a bounded cleanup loop."""
        for _ in range(6):
            if self.dismiss_known_onboarding():
                continue
            close = self._visible(self.CARD_CLOSE) or self._visible(self.SEARCH_CLOSE)
            if close:
                close.click()
                continue
            if self._visible(self.HOME) and self._visible(self.SEARCH):
                self.wait_until_ready()
                return
            raise NoSuchElementException("Maps cleanup found no known sheet or home controls")
        raise AssertionError("Maps cleanup exceeded six sheet dismissals")
