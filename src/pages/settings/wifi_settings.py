"""
Settings App - Wi-Fi Settings Page Object
"""

from typing import List, Optional

from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement

from ..base_page import BasePage


class WifiSettingsPage(BasePage):
    """
    Page object for Wi-Fi settings screen.

    Provides methods to interact with Wi-Fi settings including
    toggling Wi-Fi, connecting to networks, and viewing network details.
    """

    # Locators - iOS 26.3+ compatible
    # Note: iOS 26 uses non-breaking hyphen (Wi‑Fi) in some places
    # The Wi-Fi switch in iOS 26.3 has name="Wi‑Fi" (non-breaking hyphen)
    WIFI_SWITCH = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeSwitch' AND (name CONTAINS 'Wi-Fi' OR name CONTAINS 'Wi‑Fi')",
    )
    WIFI_HEADER = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeStaticText' AND value == 'Wi-Fi' AND label == 'Wi-Fi'",
    )

    # Network list - iOS 26.3 uses "Networks" (not "NETWORKS")
    NETWORKS_SECTION = (
        BasePage.By.IOS_PREDICATE,
        "name == 'Networks' OR name == 'NETWORKS'",
    )
    MY_NETWORKS_SECTION = (BasePage.By.ACCESSIBILITY_ID, "MY NETWORKS")
    OTHER_NETWORKS = (BasePage.By.ACCESSIBILITY_ID, "Other...")

    # Currently connected network indicator
    CONNECTED_CHECKMARK = (BasePage.By.ACCESSIBILITY_ID, "Selected")

    # Network detail screen
    FORGET_NETWORK_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Forget This Network")
    IP_ADDRESS_CELL = (BasePage.By.ACCESSIBILITY_ID, "IP Address")
    ROUTER_CELL = (BasePage.By.ACCESSIBILITY_ID, "Router")

    # Join network dialog
    NETWORK_NAME_FIELD = (BasePage.By.ACCESSIBILITY_ID, "Name")
    PASSWORD_FIELD = (BasePage.By.ACCESSIBILITY_ID, "Password")
    JOIN_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Join")
    CANCEL_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Cancel")

    # Navigation - iOS 26 uses BackButton with Settings label
    BACK_BUTTON = (
        BasePage.By.IOS_PREDICATE,
        "name == 'BackButton' OR (type == 'XCUIElementTypeButton' AND label == 'Settings')",
    )

    def __init__(self, driver: WebDriver):
        """Initialize Wi-Fi settings page."""
        super().__init__(driver)

    def is_on_wifi_page(self) -> bool:
        """
        Check if currently on Wi-Fi settings page.

        Returns:
            True if on Wi-Fi page.
        """
        # Check for Wi-Fi header text or switch
        return self.is_element_visible(self.WIFI_HEADER) or self.is_element_visible(
            self.WIFI_SWITCH
        )

    # -------------------------------------------------------------------------
    # Wi-Fi Toggle
    # -------------------------------------------------------------------------

    def is_wifi_enabled(self) -> bool:
        """
        Check if Wi-Fi is enabled.

        Returns:
            True if Wi-Fi is on.
        """
        # Re-find the element each time to avoid stale element issues
        # after toggling the switch (iOS 26.3 refreshes the UI)
        element = self.find_element(self.WIFI_SWITCH, timeout=5)
        value = element.get_attribute("value")
        return value == "1"

    def toggle_wifi(self) -> None:
        """Toggle Wi-Fi on/off."""
        import time
        from selenium.common.exceptions import StaleElementReferenceException

        # iOS 26.3: The Wi-Fi page reloads after toggling, causing stale elements
        # Use retry logic to handle this
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Re-find the element fresh each time
                element = self.find_element(self.WIFI_SWITCH, timeout=5)
                element.click()
                break
            except StaleElementReferenceException:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    raise

        # Wait for UI to settle after toggle - iOS 26.3 needs more time
        # as the entire Wi-Fi section reloads
        time.sleep(2)

    def enable_wifi(self) -> None:
        """Enable Wi-Fi if not already enabled."""
        if not self.is_wifi_enabled():
            self.toggle_wifi()

    def disable_wifi(self) -> None:
        """Disable Wi-Fi if not already disabled."""
        if self.is_wifi_enabled():
            self.toggle_wifi()

    # -------------------------------------------------------------------------
    # Network Discovery
    # -------------------------------------------------------------------------

    def get_available_networks(self) -> List[str]:
        """
        Get list of available Wi-Fi network names.

        Returns:
            List of network SSIDs.
        """
        if not self.is_wifi_enabled():
            return []

        # Wait for networks to load - iOS 26.3 may need scrolling to see Networks section
        import time

        time.sleep(2)  # Allow time for network scan

        # Try to find the Networks section, scroll if needed
        if not self.is_element_present(self.NETWORKS_SECTION, timeout=3):
            self.scroll_down()

        # Get all cells that look like network entries
        # iOS 26.3: Network cells have name like "NetworkName, Secure network, Signal strength..."
        network_cells = (
            self.By.IOS_PREDICATE,
            "type == 'XCUIElementTypeCell' AND label CONTAINS 'network'",
        )
        cells = self.find_elements(network_cells, timeout=5)

        networks = []
        for cell in cells:
            try:
                # Get the label attribute which contains the network name
                label = cell.get_attribute("label")
                if label and label not in ["Other...", "Ask to Join Networks", "Wi-Fi"]:
                    # Clean up the label - remove status indicators
                    # Format: "NetworkName, Secure network, Signal strength X of 3 bars"
                    if isinstance(label, str):
                        network_name = label.split(",")[0].strip()
                        if network_name and network_name not in networks:
                            networks.append(network_name)
            except Exception:
                continue

        return networks

    def get_connected_network(self) -> Optional[str]:
        """
        Get the name of the currently connected network.

        Returns:
            Network name or None if not connected.
        """
        if not self.is_wifi_enabled():
            return None

        # Look for cell with Selected trait (connected indicator)
        # iOS 26.3: Connected network cell has traits="Selected, Button"
        try:
            connected_cell = (
                self.By.IOS_PREDICATE,
                "type == 'XCUIElementTypeCell' AND label CONTAINS 'Signal strength'",
            )
            # Find cells that might be networks and check for Selected trait
            cells = self.find_elements(connected_cell, timeout=3)
            for cell in cells:
                # The first network cell after the Wi-Fi switch is usually the connected one
                # It has a checkmark image
                label = cell.get_attribute("label")
                if label and isinstance(label, str):
                    # Format: "NetworkName, Secure network, Signal strength X of 3 bars"
                    return label.split(",")[0].strip()
        except Exception:
            pass

        return None

    def is_connected_to_network(self, network_name: str) -> bool:
        """
        Check if connected to a specific network.

        Args:
            network_name: The network SSID to check.

        Returns:
            True if connected to the specified network.
        """
        connected = self.get_connected_network()
        return connected is not None and connected.lower() == network_name.lower()

    # -------------------------------------------------------------------------
    # Network Connection
    # -------------------------------------------------------------------------

    def select_network(self, network_name: str) -> bool:
        """
        Select a network from the list.

        Args:
            network_name: The network SSID to select.

        Returns:
            True if network was found and selected.
        """
        network_cell = (
            self.By.IOS_PREDICATE,
            f"type == 'XCUIElementTypeCell' AND label BEGINSWITH '{network_name}'",
        )

        # Try to find and click the network
        if self.scroll_to_element(network_cell):
            self.click(network_cell)
            return True
        return False

    def connect_to_network(self, network_name: str, password: Optional[str] = None) -> bool:
        """
        Connect to a Wi-Fi network.

        Args:
            network_name: The network SSID.
            password: Network password (if required).

        Returns:
            True if connection was initiated.
        """
        if not self.select_network(network_name):
            return False

        # If password field appears, enter password
        if password and self.is_element_present(self.PASSWORD_FIELD, timeout=3):
            self.send_keys(self.PASSWORD_FIELD, password)
            self.click(self.JOIN_BUTTON)

        return True

    def join_other_network(self, network_name: str, password: str, security: str = "WPA2") -> None:
        """
        Join a hidden or unlisted network.

        Args:
            network_name: The network SSID.
            password: Network password.
            security: Security type (WPA2, WPA3, etc.).
        """
        self.scroll_to_element(self.OTHER_NETWORKS)
        self.click(self.OTHER_NETWORKS)

        # Enter network details
        self.send_keys(self.NETWORK_NAME_FIELD, network_name)

        # Select security type
        security_cell = (self.By.ACCESSIBILITY_ID, "Security")
        self.click(security_cell)
        security_option = (self.By.ACCESSIBILITY_ID, security)
        self.click(security_option)
        self.tap_back_button()

        # Enter password
        self.send_keys(self.PASSWORD_FIELD, password)
        self.click(self.JOIN_BUTTON)

    # -------------------------------------------------------------------------
    # Network Details
    # -------------------------------------------------------------------------

    def open_network_details(self, network_name: str) -> bool:
        """
        Open the details/info screen for a network.

        Args:
            network_name: The network SSID.

        Returns:
            True if details screen opened.
        """
        # Find the info button for the network
        info_button = (
            self.By.IOS_PREDICATE,
            f"type == 'XCUIElementTypeButton' AND name == 'More Info' AND "
            f"ancestor::*[type == 'XCUIElementTypeCell' AND label CONTAINS '{network_name}']",
        )

        # Alternative approach - tap the (i) button directly
        network_info = (self.By.ACCESSIBILITY_ID, "More Info")

        # First select the network cell to make info button visible
        if self.select_network(network_name):
            if self.is_element_present(network_info, timeout=2):
                self.click(network_info)
                return True
        return False

    def forget_current_network(self) -> bool:
        """
        Forget the currently connected network.
        Must be on network details screen.

        Returns:
            True if network was forgotten.
        """
        if self.is_element_present(self.FORGET_NETWORK_BUTTON):
            self.click(self.FORGET_NETWORK_BUTTON)
            # Confirm forget action
            confirm = (self.By.ACCESSIBILITY_ID, "Forget")
            if self.is_element_present(confirm, timeout=3):
                self.click(confirm)
            return True
        return False

    def get_ip_address(self) -> Optional[str]:
        """
        Get the current IP address.
        Must be on network details screen.

        Returns:
            IP address string or None.
        """
        if self.is_element_present(self.IP_ADDRESS_CELL):
            return self.get_attribute(self.IP_ADDRESS_CELL, "value")
        return None

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def go_back_to_settings(self) -> None:
        """Navigate back to main Settings screen."""
        self.click(self.BACK_BUTTON)
