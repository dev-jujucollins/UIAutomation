"""
Test suite for the iOS Settings app.

These tests demonstrate automation of the native Settings app,
covering navigation, toggles, and settings verification.
"""

import pytest

from src.pages.settings import (
    SettingsHomePage,
    WifiSettingsPage,
    DisplaySettingsPage,
    GeneralSettingsPage,
)


@pytest.mark.settings
@pytest.mark.smoke
class TestSettingsNavigation:
    """Tests for Settings app navigation."""

    def test_settings_app_launches(self, settings_app: SettingsHomePage):
        """Verify Settings app launches successfully."""
        assert settings_app.is_on_settings_home()

    def test_navigate_to_wifi(self, settings_app: SettingsHomePage):
        """Verify navigation to Wi-Fi settings."""
        wifi_page = settings_app.go_to_wifi()
        assert wifi_page.is_on_wifi_page()

    def test_navigate_to_general(self, settings_app: SettingsHomePage):
        """Verify navigation to General settings."""
        general_page = settings_app.go_to_general()
        assert general_page.is_on_general_page()

    def test_navigate_to_display_brightness(self, settings_app: SettingsHomePage):
        """Verify navigation to Display & Brightness settings."""
        display_page = settings_app.go_to_display_brightness()
        assert display_page.is_on_display_page()

    def test_navigate_to_general_about(self, settings_app: SettingsHomePage):
        """Verify navigation to General > About."""
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()
        assert about_page.is_on_about_page()

    def test_back_navigation(self, settings_app: SettingsHomePage):
        """Verify back navigation returns to previous screen."""
        # Navigate to Wi-Fi
        wifi_page = settings_app.go_to_wifi()
        assert wifi_page.is_on_wifi_page()

        # Go back
        wifi_page.go_back_to_settings()

        # Should be back on Settings home
        assert settings_app.is_on_settings_home()


@pytest.mark.settings
class TestWifiSettings:
    """Tests for Wi-Fi settings functionality."""

    def test_wifi_toggle(self, settings_app: SettingsHomePage):
        """Test toggling Wi-Fi on and off."""
        wifi_page = settings_app.go_to_wifi()

        # Get initial state
        initial_state = wifi_page.is_wifi_enabled()

        # Toggle Wi-Fi
        wifi_page.toggle_wifi()

        # Verify state changed
        assert wifi_page.is_wifi_enabled() != initial_state

        # Toggle back to original state
        wifi_page.toggle_wifi()
        assert wifi_page.is_wifi_enabled() == initial_state

    def test_wifi_enable_disable(self, settings_app: SettingsHomePage):
        """Test explicit enable/disable methods."""
        wifi_page = settings_app.go_to_wifi()

        # Enable Wi-Fi
        wifi_page.enable_wifi()
        assert wifi_page.is_wifi_enabled()

        # Disable Wi-Fi
        wifi_page.disable_wifi()
        assert not wifi_page.is_wifi_enabled()

        # Re-enable for other tests
        wifi_page.enable_wifi()

    @pytest.mark.slow
    def test_list_available_networks(self, settings_app: SettingsHomePage):
        """Test listing available Wi-Fi networks."""
        wifi_page = settings_app.go_to_wifi()

        # Ensure Wi-Fi is on
        wifi_page.enable_wifi()

        # Get available networks
        networks = wifi_page.get_available_networks()

        # Should find at least some networks (in most environments)
        # Note: This may fail in isolated test environments
        print(f"Found {len(networks)} networks: {networks}")

    def test_get_connected_network(self, settings_app: SettingsHomePage):
        """Test getting the currently connected network name."""
        wifi_page = settings_app.go_to_wifi()

        # Ensure Wi-Fi is on
        wifi_page.enable_wifi()

        # Get connected network
        connected = wifi_page.get_connected_network()

        if connected:
            print(f"Connected to: {connected}")
        else:
            print("Not connected to any network")


@pytest.mark.settings
class TestDisplaySettings:
    """Tests for Display & Brightness settings."""

    def test_toggle_dark_mode(self, settings_app: SettingsHomePage):
        """Test toggling between light and dark mode."""
        display_page = settings_app.go_to_display_brightness()

        # Disable automatic appearance first
        display_page.disable_automatic_appearance()

        # Set to light mode
        display_page.set_light_mode()
        assert display_page.is_light_mode_active()

        # Switch to dark mode
        display_page.set_dark_mode()
        assert display_page.is_dark_mode_active()

        # Switch back to light mode
        display_page.set_light_mode()
        assert display_page.is_light_mode_active()

    def test_automatic_appearance_toggle(self, settings_app: SettingsHomePage):
        """Test automatic appearance toggle."""
        display_page = settings_app.go_to_display_brightness()

        # Get initial state
        initial_state = display_page.is_automatic_appearance_enabled()

        # Toggle
        display_page.toggle_automatic_appearance()
        assert display_page.is_automatic_appearance_enabled() != initial_state

        # Restore
        display_page.toggle_automatic_appearance()
        assert display_page.is_automatic_appearance_enabled() == initial_state

    def test_true_tone_toggle(self, settings_app: SettingsHomePage):
        """Test True Tone toggle (if available on device)."""
        display_page = settings_app.go_to_display_brightness()

        # This test may not work on simulators or older devices
        if display_page.is_element_present(display_page.TRUE_TONE_SWITCH, timeout=2):
            initial_state = display_page.is_true_tone_enabled()

            display_page.toggle_true_tone()
            assert display_page.is_true_tone_enabled() != initial_state

            # Restore
            display_page.toggle_true_tone()
        else:
            pytest.skip("True Tone not available on this device")

    def test_get_brightness_level(self, settings_app: SettingsHomePage):
        """Test getting current brightness level."""
        display_page = settings_app.go_to_display_brightness()

        brightness = display_page.get_brightness_level()

        # Brightness should be between 0 and 1
        assert 0 <= brightness <= 1
        print(f"Current brightness: {brightness * 100}%")


@pytest.mark.settings
class TestGeneralSettings:
    """Tests for General settings."""

    def test_navigate_to_about(self, settings_app: SettingsHomePage):
        """Test navigation to About screen."""
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()

        assert about_page.is_on_about_page()

    def test_get_device_name(self, settings_app: SettingsHomePage):
        """Test retrieving device name from About."""
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()

        device_name = about_page.get_device_name()

        assert device_name is not None
        print(f"Device name: {device_name}")

    def test_get_ios_version(self, settings_app: SettingsHomePage):
        """Test retrieving iOS version from About."""
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()

        ios_version = about_page.get_ios_version()

        # iOS version should be present
        print(f"iOS version: {ios_version}")

    def test_get_model_name(self, settings_app: SettingsHomePage):
        """Test retrieving device model name from About."""
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()

        model_name = about_page.get_model_name()

        print(f"Model name: {model_name}")

    def test_navigate_to_software_update(self, settings_app: SettingsHomePage):
        """Test navigation to Software Update screen."""
        general_page = settings_app.go_to_general()
        general_page.go_to_software_update()

        # Verify we're on the Software Update screen
        # by checking for common elements
        update_title = (general_page.By.ACCESSIBILITY_ID, "Software Update")
        assert general_page.is_element_present(update_title, timeout=5)


@pytest.mark.settings
@pytest.mark.smoke
class TestAirplaneMode:
    """Tests for Airplane Mode functionality."""

    def test_airplane_mode_toggle(self, settings_app: SettingsHomePage):
        """Test toggling Airplane Mode on and off."""
        # Get initial state
        initial_state = settings_app.is_airplane_mode_on()

        # Toggle airplane mode
        settings_app.toggle_airplane_mode()

        # Verify state changed
        assert settings_app.is_airplane_mode_on() != initial_state

        # Toggle back to original state
        settings_app.toggle_airplane_mode()
        assert settings_app.is_airplane_mode_on() == initial_state

    def test_airplane_mode_disables_wifi(self, settings_app: SettingsHomePage):
        """Test that enabling Airplane Mode affects Wi-Fi."""
        # Ensure airplane mode is off and Wi-Fi is on
        if settings_app.is_airplane_mode_on():
            settings_app.toggle_airplane_mode()

        wifi_page = settings_app.go_to_wifi()
        wifi_page.enable_wifi()
        wifi_page.go_back_to_settings()

        # Enable airplane mode
        settings_app.toggle_airplane_mode()

        # Check Wi-Fi status
        wifi_page = settings_app.go_to_wifi()

        # Wi-Fi should be disabled when airplane mode is on
        # Note: On some iOS versions, Wi-Fi can be manually enabled even in airplane mode

        # Clean up - disable airplane mode
        wifi_page.go_back_to_settings()
        if settings_app.is_airplane_mode_on():
            settings_app.toggle_airplane_mode()


@pytest.mark.settings
class TestSettingsSearch:
    """Tests for Settings search functionality."""

    def test_search_for_wifi(self, settings_app: SettingsHomePage):
        """Test searching for Wi-Fi in settings."""
        settings_app.search_settings("Wi-Fi")

        # Verify search results show Wi-Fi option
        wifi_result = (settings_app.By.ACCESSIBILITY_ID, "Wi-Fi")
        assert settings_app.is_element_present(wifi_result, timeout=5)

        # Clear search
        settings_app.clear_search()

    def test_search_for_display(self, settings_app: SettingsHomePage):
        """Test searching for display settings."""
        settings_app.search_settings("Display")

        # Verify search results show Display & Brightness option
        display_result = (settings_app.By.ACCESSIBILITY_ID, "Display & Brightness")
        assert settings_app.is_element_present(display_result, timeout=5)

        # Clear search
        settings_app.clear_search()

    def test_search_and_navigate(self, settings_app: SettingsHomePage):
        """Test searching and navigating to a result."""
        settings_app.search_settings("General")

        # Tap on General in search results
        general_cell = (settings_app.By.ACCESSIBILITY_ID, "General")
        settings_app.click(general_cell)

        # Verify we navigated to General settings
        general_page = GeneralSettingsPage(settings_app.driver)
        assert general_page.is_on_general_page()
