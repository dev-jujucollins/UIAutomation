"""
Settings App - General Settings Page Object
"""

from typing import Optional

from appium.webdriver.webdriver import WebDriver

from ..base_page import BasePage


class GeneralSettingsPage(BasePage):
    """
    Page object for General settings screen.

    Provides methods to interact with general device settings including
    About, Software Update, AirDrop, Storage, and more.
    """

    # Locators - iOS 26.3 compatible (uses cell name identifiers)
    ABOUT_CELL = (BasePage.By.ACCESSIBILITY_ID, "About")
    SOFTWARE_UPDATE_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'SOFTWARE_UPDATE_LINK' OR label == 'Software Update'",
    )
    AIRDROP_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'AIRDROP_LINK' OR label == 'AirDrop'",
    )
    AIRDROP_HANDOFF_CELL = (BasePage.By.ACCESSIBILITY_ID, "AirDrop & Handoff")
    AIRPLAY_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'CONTINUITY_SPEC' OR label CONTAINS 'AirPlay'",
    )

    # Storage & Usage
    IPHONE_STORAGE_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'STORAGE_MGMT' OR label == 'iPhone Storage'",
    )
    BACKGROUND_REFRESH_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'AUTO_CONTENT_DOWNLOAD' OR label == 'Background App Refresh'",
    )

    # Date & Time
    DATE_TIME_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'DATE_AND_TIME' OR label CONTAINS 'Date'",
    )

    # Keyboard
    KEYBOARD_CELL = (BasePage.By.ACCESSIBILITY_ID, "Keyboard")

    # Language & Region
    LANGUAGE_REGION_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'INTERNATIONAL' OR label CONTAINS 'Language'",
    )

    # Dictionary
    DICTIONARY_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'DICTIONARY' OR label == 'Dictionary'",
    )

    # VPN & Device Management
    VPN_CELL = (BasePage.By.ACCESSIBILITY_ID, "VPN & Device Management")

    # Reset options
    TRANSFER_RESET_CELL = (BasePage.By.ACCESSIBILITY_ID, "Transfer or Reset iPhone")

    # Shut Down
    SHUT_DOWN_CELL = (BasePage.By.ACCESSIBILITY_ID, "Shut Down")

    # Navigation - iOS 26.3 uses BackButton
    BACK_BUTTON = (
        BasePage.By.IOS_PREDICATE,
        "name == 'BackButton' OR label == 'Settings'",
    )

    def __init__(self, driver: WebDriver):
        """Initialize General settings page."""
        super().__init__(driver)

    def is_on_general_page(self) -> bool:
        """
        Check if currently on General settings page.

        Returns:
            True if on General page.
        """
        return self.is_element_visible(self.ABOUT_CELL)

    # -------------------------------------------------------------------------
    # About Section
    # -------------------------------------------------------------------------

    def go_to_about(self) -> "AboutPage":
        """
        Navigate to About screen.

        Returns:
            AboutPage instance.
        """
        self.click(self.ABOUT_CELL)
        return AboutPage(self.driver)

    # -------------------------------------------------------------------------
    # Software Update
    # -------------------------------------------------------------------------

    def go_to_software_update(self) -> None:
        """Navigate to Software Update screen."""
        self.click(self.SOFTWARE_UPDATE_CELL)

    # -------------------------------------------------------------------------
    # AirDrop
    # -------------------------------------------------------------------------

    def go_to_airdrop(self) -> None:
        """Navigate to AirDrop settings."""
        # Try newer iOS structure first
        if self.is_element_present(self.AIRDROP_HANDOFF_CELL, timeout=2):
            self.click(self.AIRDROP_HANDOFF_CELL)
        elif self.is_element_present(self.AIRDROP_CELL, timeout=2):
            self.click(self.AIRDROP_CELL)

    # -------------------------------------------------------------------------
    # Storage
    # -------------------------------------------------------------------------

    def go_to_iphone_storage(self) -> None:
        """Navigate to iPhone Storage screen."""
        self.scroll_to_element(self.IPHONE_STORAGE_CELL)
        self.click(self.IPHONE_STORAGE_CELL)

    # -------------------------------------------------------------------------
    # Background App Refresh
    # -------------------------------------------------------------------------

    def go_to_background_app_refresh(self) -> None:
        """Navigate to Background App Refresh settings."""
        self.scroll_to_element(self.BACKGROUND_REFRESH_CELL)
        self.click(self.BACKGROUND_REFRESH_CELL)

    # -------------------------------------------------------------------------
    # Date & Time
    # -------------------------------------------------------------------------

    def go_to_date_time(self) -> None:
        """Navigate to Date & Time settings."""
        self.scroll_to_element(self.DATE_TIME_CELL)
        self.click(self.DATE_TIME_CELL)

    # -------------------------------------------------------------------------
    # Keyboard
    # -------------------------------------------------------------------------

    def go_to_keyboard(self) -> None:
        """Navigate to Keyboard settings."""
        self.scroll_to_element(self.KEYBOARD_CELL)
        self.click(self.KEYBOARD_CELL)

    # -------------------------------------------------------------------------
    # Language & Region
    # -------------------------------------------------------------------------

    def go_to_language_region(self) -> None:
        """Navigate to Language & Region settings."""
        self.scroll_to_element(self.LANGUAGE_REGION_CELL)
        self.click(self.LANGUAGE_REGION_CELL)

    # -------------------------------------------------------------------------
    # VPN & Device Management
    # -------------------------------------------------------------------------

    def go_to_vpn(self) -> None:
        """Navigate to VPN & Device Management settings."""
        self.scroll_to_element(self.VPN_CELL)
        self.click(self.VPN_CELL)

    # -------------------------------------------------------------------------
    # Transfer or Reset
    # -------------------------------------------------------------------------

    def go_to_transfer_reset(self) -> None:
        """Navigate to Transfer or Reset iPhone settings."""
        self.scroll_to_element(self.TRANSFER_RESET_CELL)
        self.click(self.TRANSFER_RESET_CELL)

    # -------------------------------------------------------------------------
    # Shut Down
    # -------------------------------------------------------------------------

    def go_to_shut_down(self) -> None:
        """Navigate to Shut Down screen."""
        self.scroll_to_element(self.SHUT_DOWN_CELL)
        self.click(self.SHUT_DOWN_CELL)

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def go_back_to_settings(self) -> None:
        """Navigate back to main Settings screen."""
        self.click(self.BACK_BUTTON)


class AboutPage(BasePage):
    """
    Page object for the About screen under General settings.

    Provides methods to retrieve device information.
    """

    # Locators - iOS 26.3 compatible (uses cell name identifiers)
    NAME_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'NAME_CELL_ID' OR label CONTAINS 'Name,'",
    )
    IOS_VERSION_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'SW_VERSION_SPECIFIER' OR label CONTAINS 'iOS Version'",
    )
    SOFTWARE_VERSION_CELL = (BasePage.By.ACCESSIBILITY_ID, "Software Version")
    MODEL_NAME_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'ProductModelName' OR label CONTAINS 'Model Name'",
    )
    MODEL_NUMBER_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'ProductModel' OR label CONTAINS 'Model Number'",
    )
    SERIAL_NUMBER_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'SerialNumber' OR label CONTAINS 'Serial Number'",
    )
    WIFI_ADDRESS_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'MACAddress' OR label CONTAINS 'Wi-Fi Address'",
    )
    BLUETOOTH_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'BTMACAddress' OR label CONTAINS 'Bluetooth'",
    )

    # Storage - iOS 26.3 uses uppercase names
    SONGS_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'SONGS' OR label CONTAINS 'Songs'",
    )
    VIDEOS_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'VIDEOS' OR label CONTAINS 'Videos'",
    )
    PHOTOS_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'PHOTOS' OR label CONTAINS 'Photos'",
    )
    APPLICATIONS_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'APPLICATIONS' OR label CONTAINS 'Applications'",
    )
    CAPACITY_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'User Data Capacity' OR label CONTAINS 'Capacity'",
    )
    AVAILABLE_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'User Data Available' OR label CONTAINS 'Available'",
    )

    # Navigation - iOS 26.3 uses BackButton
    BACK_BUTTON = (
        BasePage.By.IOS_PREDICATE,
        "name == 'BackButton' OR label == 'General'",
    )

    def __init__(self, driver: WebDriver):
        """Initialize About page."""
        super().__init__(driver)

    def is_on_about_page(self) -> bool:
        """
        Check if currently on About page.

        Returns:
            True if on About page.
        """
        return self.is_element_visible(self.NAME_CELL)

    def _extract_value_from_label(self, label: Optional[str]) -> Optional[str]:
        """
        Extract the value part from an iOS 26.3 label.

        iOS 26.3 format: "Field Name, Value" (e.g., "Name, Julius iPhone")

        Args:
            label: The full label string.

        Returns:
            The extracted value or None.
        """
        if label and isinstance(label, str) and "," in label:
            parts = label.split(",", 1)
            if len(parts) > 1:
                return parts[1].strip()
        return label

    def get_device_name(self) -> Optional[str]:
        """
        Get the device name.

        Returns:
            Device name string.
        """
        # iOS 26.3: Value is in the label, format "Name, DeviceName"
        element = self.find_element(self.NAME_CELL, timeout=5)
        label = element.get_attribute("label")
        return self._extract_value_from_label(label)

    def get_ios_version(self) -> Optional[str]:
        """
        Get the iOS version.

        Returns:
            iOS version string.
        """
        # iOS 26.3: format "iOS Version, 26.3"
        if self.is_element_present(self.IOS_VERSION_CELL, timeout=2):
            element = self.find_element(self.IOS_VERSION_CELL)
            label = element.get_attribute("label")
            return self._extract_value_from_label(label)
        elif self.is_element_present(self.SOFTWARE_VERSION_CELL, timeout=2):
            element = self.find_element(self.SOFTWARE_VERSION_CELL)
            label = element.get_attribute("label")
            return self._extract_value_from_label(label)
        return None

    def get_model_name(self) -> Optional[str]:
        """
        Get the device model name.

        Returns:
            Model name string (e.g., "iPhone 15 Pro").
        """
        self.scroll_to_element(self.MODEL_NAME_CELL)
        if self.is_element_present(self.MODEL_NAME_CELL):
            element = self.find_element(self.MODEL_NAME_CELL)
            label = element.get_attribute("label")
            return self._extract_value_from_label(label)
        return None

    def get_model_number(self) -> Optional[str]:
        """
        Get the device model number.

        Returns:
            Model number string.
        """
        self.scroll_to_element(self.MODEL_NUMBER_CELL)
        if self.is_element_present(self.MODEL_NUMBER_CELL):
            element = self.find_element(self.MODEL_NUMBER_CELL)
            label = element.get_attribute("label")
            return self._extract_value_from_label(label)
        return None

    def get_serial_number(self) -> Optional[str]:
        """
        Get the device serial number.

        Returns:
            Serial number string.
        """
        self.scroll_to_element(self.SERIAL_NUMBER_CELL)
        if self.is_element_present(self.SERIAL_NUMBER_CELL):
            element = self.find_element(self.SERIAL_NUMBER_CELL)
            label = element.get_attribute("label")
            return self._extract_value_from_label(label)
        return None

    def get_wifi_address(self) -> Optional[str]:
        """
        Get the Wi-Fi MAC address.

        Returns:
            Wi-Fi address string.
        """
        self.scroll_to_element(self.WIFI_ADDRESS_CELL)
        if self.is_element_present(self.WIFI_ADDRESS_CELL):
            element = self.find_element(self.WIFI_ADDRESS_CELL)
            label = element.get_attribute("label")
            return self._extract_value_from_label(label)
        return None

    def get_storage_capacity(self) -> Optional[str]:
        """
        Get the total storage capacity.

        Returns:
            Capacity string (e.g., "256 GB").
        """
        self.scroll_to_element(self.CAPACITY_CELL)
        if self.is_element_present(self.CAPACITY_CELL):
            element = self.find_element(self.CAPACITY_CELL)
            label = element.get_attribute("label")
            return self._extract_value_from_label(label)
        return None

    def get_available_storage(self) -> Optional[str]:
        """
        Get the available storage space.

        Returns:
            Available storage string (e.g., "128 GB").
        """
        self.scroll_to_element(self.AVAILABLE_CELL)
        if self.is_element_present(self.AVAILABLE_CELL):
            element = self.find_element(self.AVAILABLE_CELL)
            label = element.get_attribute("label")
            return self._extract_value_from_label(label)
        return None

    def go_back_to_general(self) -> None:
        """Navigate back to General settings."""
        self.click(self.BACK_BUTTON)
