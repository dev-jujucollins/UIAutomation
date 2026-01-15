"""
Settings App - Display & Brightness Settings Page Object
"""

from typing import Optional

from appium.webdriver.webdriver import WebDriver

from ..base_page import BasePage


class DisplaySettingsPage(BasePage):
    """
    Page object for Display & Brightness settings screen.

    Provides methods to interact with display settings including
    brightness, appearance (light/dark mode), text size, and more.
    """

    # Locators - Appearance (iOS 26.3 compatible)
    # iOS 26.3 uses DBSDeviceAppearanceOptionLight/Dark for Light/Dark buttons
    LIGHT_MODE_BUTTON = (
        BasePage.By.IOS_PREDICATE,
        "name == 'DBSDeviceAppearanceOptionLight' OR label == 'Light'",
    )
    DARK_MODE_BUTTON = (
        BasePage.By.IOS_PREDICATE,
        "name == 'DBSDeviceAppearanceOptionDark' OR label == 'Dark'",
    )
    # iOS 26.3: Automatic switch has name="AUTOMATIC" (uppercase)
    # There's an outer switch container and an inner actual switch
    AUTOMATIC_SWITCH = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeSwitch' AND (name == 'AUTOMATIC' OR name == 'Automatic')",
    )
    # The actual clickable inner switch (no name attribute)
    AUTOMATIC_SWITCH_INNER = (
        BasePage.By.IOS_CLASS_CHAIN,
        "**/XCUIElementTypeSwitch[`name == 'AUTOMATIC'`]/XCUIElementTypeSwitch",
    )

    # Brightness slider - iOS 26.3: name="Screen brightness" inside cell name="BRIGHTNESS"
    BRIGHTNESS_SLIDER = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeSlider' AND (name == 'Screen brightness' OR name == 'Brightness')",
    )

    # True Tone - iOS 26.3: name="WHITE_BALANCE" with label="True Tone"
    TRUE_TONE_SWITCH = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeSwitch' AND (name == 'WHITE_BALANCE' OR name == 'True Tone')",
    )
    # The actual clickable inner switch for True Tone
    TRUE_TONE_SWITCH_INNER = (
        BasePage.By.IOS_CLASS_CHAIN,
        "**/XCUIElementTypeSwitch[`name == 'WHITE_BALANCE'`]/XCUIElementTypeSwitch",
    )

    # Night Shift
    NIGHT_SHIFT_CELL = (BasePage.By.ACCESSIBILITY_ID, "Night Shift")

    # Auto-Lock
    AUTO_LOCK_CELL = (BasePage.By.ACCESSIBILITY_ID, "Auto-Lock")

    # Raise to Wake
    RAISE_TO_WAKE_SWITCH = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeSwitch' AND name == 'Raise to Wake'",
    )

    # Text Size
    TEXT_SIZE_CELL = (BasePage.By.ACCESSIBILITY_ID, "Text Size")

    # Bold Text
    BOLD_TEXT_SWITCH = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeSwitch' AND name == 'Bold Text'",
    )

    # Display Zoom
    DISPLAY_ZOOM_CELL = (BasePage.By.ACCESSIBILITY_ID, "Display Zoom")

    # Navigation
    BACK_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Settings")

    def __init__(self, driver: WebDriver):
        """Initialize Display & Brightness settings page."""
        super().__init__(driver)

    def is_on_display_page(self) -> bool:
        """
        Check if currently on Display & Brightness page.

        Returns:
            True if on Display page.
        """
        # Check for Display & Brightness header or Light/Dark buttons
        display_header = (
            self.By.IOS_PREDICATE,
            "label == 'Display & Brightness' AND type == 'XCUIElementTypeStaticText'",
        )
        return (
            self.is_element_visible(display_header)
            or self.is_element_visible(self.LIGHT_MODE_BUTTON)
            or self.is_element_visible(self.DARK_MODE_BUTTON)
        )

    # -------------------------------------------------------------------------
    # Appearance Mode
    # -------------------------------------------------------------------------

    def set_light_mode(self) -> None:
        """Set appearance to Light mode."""
        self.click(self.LIGHT_MODE_BUTTON)

    def set_dark_mode(self) -> None:
        """Set appearance to Dark mode."""
        self.click(self.DARK_MODE_BUTTON)

    def is_dark_mode_active(self) -> bool:
        """
        Check if Dark mode is currently active.

        Returns:
            True if Dark mode is active.
        """
        # Check if dark mode button is selected
        # iOS 26.3: The button has value="1" when selected
        element = self.find_element(self.DARK_MODE_BUTTON)
        selected = element.get_attribute("selected")
        value = element.get_attribute("value")
        return selected == "true" or selected == "1" or value == "1"

    def is_light_mode_active(self) -> bool:
        """
        Check if Light mode is currently active.

        Returns:
            True if Light mode is active.
        """
        # iOS 26.3: The button has value="1" when selected
        element = self.find_element(self.LIGHT_MODE_BUTTON)
        selected = element.get_attribute("selected")
        value = element.get_attribute("value")
        return selected == "true" or selected == "1" or value == "1"

    def toggle_automatic_appearance(self) -> None:
        """Toggle automatic appearance switching."""
        import time

        # iOS 26.3: Need to click the inner switch element, not the outer container
        if self.is_element_present(self.AUTOMATIC_SWITCH_INNER, timeout=2):
            self.click(self.AUTOMATIC_SWITCH_INNER)
        else:
            self.click(self.AUTOMATIC_SWITCH)
        # Wait for UI to settle after toggle
        time.sleep(1)

    def is_automatic_appearance_enabled(self) -> bool:
        """
        Check if automatic appearance is enabled.

        Returns:
            True if automatic is enabled.
        """
        # Re-find element each time to avoid stale element issues
        element = self.find_element(self.AUTOMATIC_SWITCH, timeout=5)
        value = element.get_attribute("value")
        return value == "1"

    def enable_automatic_appearance(self) -> None:
        """Enable automatic appearance if not already enabled."""
        if not self.is_automatic_appearance_enabled():
            self.toggle_automatic_appearance()

    def disable_automatic_appearance(self) -> None:
        """Disable automatic appearance if currently enabled."""
        if self.is_automatic_appearance_enabled():
            self.toggle_automatic_appearance()

    # -------------------------------------------------------------------------
    # Brightness
    # -------------------------------------------------------------------------

    def get_brightness_level(self) -> float:
        """
        Get the current brightness level.

        Returns:
            Brightness level between 0.0 and 1.0.
        """
        value = self.get_attribute(self.BRIGHTNESS_SLIDER, "value")
        if value:
            # Value comes as percentage string like "50%"
            try:
                return float(value.replace("%", "")) / 100
            except ValueError:
                return 0.5
        return 0.5

    def set_brightness_level(self, level: float) -> None:
        """
        Set brightness level.

        Args:
            level: Brightness level between 0.0 and 1.0.
        """
        # Clamp value between 0 and 1
        level = max(0.0, min(1.0, level))

        slider = self.find_element(self.BRIGHTNESS_SLIDER)

        # Get slider dimensions
        rect = slider.rect
        start_x = rect["x"]
        width = rect["width"]
        y = rect["y"] + rect["height"] / 2

        # Calculate target position
        target_x = start_x + (width * level)

        # Tap at target position
        self.driver.execute_script("mobile: tap", {"x": target_x, "y": y})

    # -------------------------------------------------------------------------
    # True Tone
    # -------------------------------------------------------------------------

    def is_true_tone_enabled(self) -> bool:
        """
        Check if True Tone is enabled.

        Returns:
            True if True Tone is enabled.
        """
        if self.is_element_present(self.TRUE_TONE_SWITCH, timeout=2):
            value = self.get_attribute(self.TRUE_TONE_SWITCH, "value")
            return value == "1"
        return False

    def toggle_true_tone(self) -> None:
        """Toggle True Tone on/off."""
        import time

        # iOS 26.3: Need to click the inner switch element, not the outer container
        if self.is_element_present(self.TRUE_TONE_SWITCH_INNER, timeout=2):
            self.click(self.TRUE_TONE_SWITCH_INNER)
            time.sleep(1)
        elif self.is_element_present(self.TRUE_TONE_SWITCH):
            self.click(self.TRUE_TONE_SWITCH)
            time.sleep(1)

    def enable_true_tone(self) -> None:
        """Enable True Tone if not already enabled."""
        if not self.is_true_tone_enabled():
            self.toggle_true_tone()

    def disable_true_tone(self) -> None:
        """Disable True Tone if currently enabled."""
        if self.is_true_tone_enabled():
            self.toggle_true_tone()

    # -------------------------------------------------------------------------
    # Night Shift
    # -------------------------------------------------------------------------

    def go_to_night_shift(self) -> None:
        """Navigate to Night Shift settings."""
        self.scroll_to_element(self.NIGHT_SHIFT_CELL)
        self.click(self.NIGHT_SHIFT_CELL)

    # -------------------------------------------------------------------------
    # Auto-Lock
    # -------------------------------------------------------------------------

    def go_to_auto_lock(self) -> None:
        """Navigate to Auto-Lock settings."""
        self.scroll_to_element(self.AUTO_LOCK_CELL)
        self.click(self.AUTO_LOCK_CELL)

    def get_auto_lock_duration(self) -> Optional[str]:
        """
        Get the current Auto-Lock duration.

        Returns:
            Duration string (e.g., "30 Seconds", "1 Minute", "Never").
        """
        if self.is_element_present(self.AUTO_LOCK_CELL):
            return self.get_attribute(self.AUTO_LOCK_CELL, "value")
        return None

    def set_auto_lock_duration(self, duration: str) -> None:
        """
        Set Auto-Lock duration.

        Args:
            duration: Duration option (e.g., "30 Seconds", "1 Minute", "5 Minutes", "Never").
        """
        self.go_to_auto_lock()
        duration_option = (self.By.ACCESSIBILITY_ID, duration)
        self.click(duration_option)
        self.tap_back_button()

    # -------------------------------------------------------------------------
    # Raise to Wake
    # -------------------------------------------------------------------------

    def is_raise_to_wake_enabled(self) -> bool:
        """
        Check if Raise to Wake is enabled.

        Returns:
            True if Raise to Wake is enabled.
        """
        if self.is_element_present(self.RAISE_TO_WAKE_SWITCH, timeout=2):
            value = self.get_attribute(self.RAISE_TO_WAKE_SWITCH, "value")
            return value == "1"
        return False

    def toggle_raise_to_wake(self) -> None:
        """Toggle Raise to Wake on/off."""
        if self.is_element_present(self.RAISE_TO_WAKE_SWITCH):
            self.click(self.RAISE_TO_WAKE_SWITCH)

    # -------------------------------------------------------------------------
    # Text Size & Bold Text
    # -------------------------------------------------------------------------

    def go_to_text_size(self) -> None:
        """Navigate to Text Size settings."""
        self.scroll_to_element(self.TEXT_SIZE_CELL)
        self.click(self.TEXT_SIZE_CELL)

    def is_bold_text_enabled(self) -> bool:
        """
        Check if Bold Text is enabled.

        Returns:
            True if Bold Text is enabled.
        """
        self.scroll_to_element(self.BOLD_TEXT_SWITCH)
        if self.is_element_present(self.BOLD_TEXT_SWITCH, timeout=2):
            value = self.get_attribute(self.BOLD_TEXT_SWITCH, "value")
            return value == "1"
        return False

    def toggle_bold_text(self) -> None:
        """
        Toggle Bold Text on/off.

        Note: This may trigger a device restart prompt.
        """
        self.scroll_to_element(self.BOLD_TEXT_SWITCH)
        if self.is_element_present(self.BOLD_TEXT_SWITCH):
            self.click(self.BOLD_TEXT_SWITCH)

    # -------------------------------------------------------------------------
    # Display Zoom
    # -------------------------------------------------------------------------

    def go_to_display_zoom(self) -> None:
        """Navigate to Display Zoom settings."""
        self.scroll_to_element(self.DISPLAY_ZOOM_CELL)
        self.click(self.DISPLAY_ZOOM_CELL)

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def go_back_to_settings(self) -> None:
        """Navigate back to main Settings screen."""
        self.click(self.BACK_BUTTON)
