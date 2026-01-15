"""
Settings App - Home Page Object
"""

from typing import List, Optional

from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement

from ..base_page import BasePage


class SettingsHomePage(BasePage):
    """
    Page object for the main Settings app home screen.

    Provides methods to navigate to various settings sections.
    """

    # Locators - iOS 26+ uses name attribute with com.apple.settings.* identifiers
    # iOS 26.3: Search field is XCUIElementTypeSearchField in the toolbar at bottom
    SEARCH_FIELD = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeSearchField' AND name == 'Search'",
    )

    # Main sections - using name attribute for iOS 26+ compatibility
    APPLE_ID_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.primaryAppleAccount'",
    )
    AIRPLANE_MODE = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.airplaneMode'",
    )
    WIFI_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.wifi'",
    )
    BLUETOOTH_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.bluetooth'",
    )
    CELLULAR_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.cellular'",
    )
    PERSONAL_HOTSPOT_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.personalHotspot'",
    )

    NOTIFICATIONS_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.notifications'",
    )
    SOUNDS_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.sounds'",
    )
    FOCUS_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.focus'",
    )
    SCREEN_TIME_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.screenTime'",
    )

    GENERAL_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.general'",
    )
    CONTROL_CENTER_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.controlCenter'",
    )
    DISPLAY_BRIGHTNESS_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.displayAndBrightness'",
    )
    HOME_SCREEN_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.homeScreen'",
    )
    ACCESSIBILITY_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.accessibility'",
    )
    WALLPAPER_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.wallpaper'",
    )

    SIRI_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.siri'",
    )
    FACE_ID_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.faceID'",
    )
    EMERGENCY_SOS_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.emergencySOS'",
    )

    BATTERY_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.battery'",
    )
    PRIVACY_CELL = (
        BasePage.By.IOS_PREDICATE,
        "name == 'com.apple.settings.privacy'",
    )

    # Collection view for scrolling (iOS 26 uses CollectionView instead of Table)
    SETTINGS_COLLECTION = (BasePage.By.IOS_CLASS_CHAIN, "**/XCUIElementTypeCollectionView[1]")

    def __init__(self, driver: WebDriver):
        """Initialize Settings home page."""
        super().__init__(driver)

    def is_on_settings_home(self) -> bool:
        """
        Check if currently on Settings home page.

        Returns:
            True if on Settings home.
        """
        return self.is_element_visible(self.GENERAL_CELL) or self.is_element_visible(self.WIFI_CELL)

    # -------------------------------------------------------------------------
    # Search Functionality
    # -------------------------------------------------------------------------

    def search_settings(self, query: str) -> None:
        """
        Search within settings.

        Args:
            query: Search text.
        """
        # iOS 26.3: Search field is in the toolbar at the bottom of the screen
        # No need to scroll - just tap the search field directly
        import time

        # Wait for search field to be available
        self.wait_for_clickable(self.SEARCH_FIELD, timeout=5)
        self.click(self.SEARCH_FIELD)
        time.sleep(0.5)  # Wait for keyboard to appear

        # Send keys to the search field
        self.send_keys(self.SEARCH_FIELD, query, clear_first=True)

    def clear_search(self) -> None:
        """Clear the search field."""
        cancel_button = (self.By.ACCESSIBILITY_ID, "Cancel")
        if self.is_element_present(cancel_button):
            self.click(cancel_button)

    # -------------------------------------------------------------------------
    # Navigation Methods - Network Section
    # -------------------------------------------------------------------------

    def go_to_wifi(self) -> "WifiSettingsPage":
        """
        Navigate to Wi-Fi settings.

        Returns:
            WifiSettingsPage instance.
        """
        from .wifi_settings import WifiSettingsPage

        self.click(self.WIFI_CELL)
        return WifiSettingsPage(self.driver)

    def go_to_bluetooth(self) -> None:
        """Navigate to Bluetooth settings."""
        self.click(self.BLUETOOTH_CELL)

    def go_to_cellular(self) -> None:
        """Navigate to Cellular settings."""
        self.click(self.CELLULAR_CELL)

    def toggle_airplane_mode(self) -> None:
        """Toggle airplane mode switch."""
        # iOS 26: The actual toggle is the inner XCUIElementTypeSwitch without a name
        # inside the parent element with name='com.apple.settings.airplaneMode'
        inner_switch = (
            self.By.IOS_CLASS_CHAIN,
            "**/XCUIElementTypeSwitch[`name == 'com.apple.settings.airplaneMode'`]"
            "/XCUIElementTypeSwitch",
        )
        # Try inner switch first, fall back to parent element
        if self.is_element_present(inner_switch, timeout=2):
            self.click(inner_switch)
        else:
            self.click(self.AIRPLANE_MODE)
        # Wait for the toggle animation to complete
        import time

        time.sleep(1)

    def is_airplane_mode_on(self) -> bool:
        """
        Check if airplane mode is enabled.

        Returns:
            True if airplane mode is on.
        """
        # iOS 26: The parent switch element has the value
        element = self.find_element(self.AIRPLANE_MODE, timeout=5)
        value = element.get_attribute("value")
        return value == "1"

    # -------------------------------------------------------------------------
    # Navigation Methods - General Section
    # -------------------------------------------------------------------------

    def go_to_general(self) -> "GeneralSettingsPage":
        """
        Navigate to General settings.

        Returns:
            GeneralSettingsPage instance.
        """
        from .general_settings import GeneralSettingsPage

        self.scroll_to_element(self.GENERAL_CELL)
        self.click(self.GENERAL_CELL)
        return GeneralSettingsPage(self.driver)

    def go_to_display_brightness(self) -> "DisplaySettingsPage":
        """
        Navigate to Display & Brightness settings.

        Returns:
            DisplaySettingsPage instance.
        """
        from .display_settings import DisplaySettingsPage
        from appium.webdriver.common.appiumby import AppiumBy

        # Display & Brightness requires scrolling in iOS 26+
        # Scroll down until we find it
        for _ in range(5):
            try:
                element = self.driver.find_element(
                    AppiumBy.IOS_PREDICATE, "name == 'com.apple.settings.displayAndBrightness'"
                )
                element.click()
                return DisplaySettingsPage(self.driver)
            except Exception:
                self.scroll_down()

        # Final attempt with wait
        self.click(self.DISPLAY_BRIGHTNESS_CELL)
        return DisplaySettingsPage(self.driver)

    def go_to_accessibility(self) -> None:
        """Navigate to Accessibility settings."""
        self.scroll_to_element(self.ACCESSIBILITY_CELL)
        self.click(self.ACCESSIBILITY_CELL)

    def go_to_notifications(self) -> None:
        """Navigate to Notifications settings."""
        self.scroll_to_element(self.NOTIFICATIONS_CELL)
        self.click(self.NOTIFICATIONS_CELL)

    def go_to_screen_time(self) -> None:
        """Navigate to Screen Time settings."""
        self.scroll_to_element(self.SCREEN_TIME_CELL)
        self.click(self.SCREEN_TIME_CELL)

    # -------------------------------------------------------------------------
    # Navigation Methods - Privacy & Security Section
    # -------------------------------------------------------------------------

    def go_to_privacy(self) -> None:
        """Navigate to Privacy & Security settings."""
        self.scroll_to_element(self.PRIVACY_CELL)
        self.click(self.PRIVACY_CELL)

    def go_to_face_id(self) -> None:
        """Navigate to Face ID & Passcode settings."""
        self.scroll_to_element(self.FACE_ID_CELL)
        self.click(self.FACE_ID_CELL)

    # -------------------------------------------------------------------------
    # Navigation Methods - Other Sections
    # -------------------------------------------------------------------------

    def go_to_battery(self) -> None:
        """Navigate to Battery settings."""
        self.scroll_to_element(self.BATTERY_CELL)
        self.click(self.BATTERY_CELL)

    def go_to_siri(self) -> None:
        """Navigate to Siri & Search settings."""
        self.scroll_to_element(self.SIRI_CELL)
        self.click(self.SIRI_CELL)

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def get_visible_settings_cells(self) -> List[WebElement]:
        """
        Get all visible settings cells.

        Returns:
            List of cell WebElements.
        """
        cells_locator = (
            self.By.IOS_CLASS_CHAIN,
            "**/XCUIElementTypeTable/XCUIElementTypeCell",
        )
        return self.find_elements(cells_locator)

    def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of settings list."""
        for _ in range(10):
            self.scroll_down()

    def scroll_to_top(self) -> None:
        """Scroll to the top of settings list."""
        for _ in range(10):
            self.scroll_up()
