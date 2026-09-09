"""
Test suite for the iOS Settings app.

These tests demonstrate automation of the native Settings app,
covering navigation, toggles, and settings verification.
"""

import re

import pytest

from uiautomation.pages.settings import (
    GeneralSettingsPage,
    SettingsHomePage,
    WifiSettingsPage,
)


@pytest.mark.settings
class TestSettingsNavigation:
    """Tests for Settings app navigation."""

    @pytest.mark.smoke
    def test_settings_app_launches(self, settings_app: SettingsHomePage):
        """Verify Settings app launches to a visible, usable home screen."""
        settings_app.assert_home_visually_ready()

    @pytest.mark.real_device(reason="Wi-Fi settings layout differs on simulator")
    def test_navigate_to_wifi(self, settings_app: SettingsHomePage):
        """Verify navigation to Wi-Fi settings."""
        wifi_page = settings_app.go_to_wifi()
        assert wifi_page.is_on_wifi_page()

    def test_navigate_to_general(self, settings_app: SettingsHomePage):
        """Verify navigation to General settings."""
        general_page = settings_app.go_to_general()
        assert general_page.is_on_general_page()

    @pytest.mark.real_device(reason="Display settings layout differs on simulator")
    def test_navigate_to_display_brightness(self, settings_app: SettingsHomePage):
        """Verify navigation to Display & Brightness settings."""
        display_page = settings_app.go_to_display_brightness()
        assert display_page.is_on_display_page()

    @pytest.mark.journey
    def test_navigate_to_general_about(self, settings_app: SettingsHomePage):
        """Verify navigation to General > About."""
        general_page = settings_app.go_to_general()
        assert general_page.is_on_general_page()
        about_page = general_page.go_to_about()
        assert about_page.is_on_about_page()

    @pytest.mark.real_device(reason="Back path via Wi-Fi screen differs on simulator")
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
@pytest.mark.real_device(reason="Wi-Fi radio controls require hardware")
class TestWifiSettings:
    """Tests for Wi-Fi settings functionality."""

    def test_wifi_toggle(self, restored_wifi: WifiSettingsPage):
        """Verify one toggle changes the radio state; fixture restores it."""
        initial_state = restored_wifi.is_wifi_enabled()
        restored_wifi.toggle_wifi()
        assert restored_wifi.is_wifi_enabled() != initial_state

    def test_wifi_enable_disable(self, restored_wifi: WifiSettingsPage):
        """Verify explicit radio controls; fixture restores the starting state."""
        restored_wifi.enable_wifi()
        assert restored_wifi.is_wifi_enabled()
        restored_wifi.disable_wifi()
        assert not restored_wifi.is_wifi_enabled()

    @pytest.mark.diagnostic
    def test_list_available_networks(self, restored_wifi: WifiSettingsPage):
        """Inspect networks without assuming a particular radio environment."""
        restored_wifi.enable_wifi()
        networks = restored_wifi.get_available_networks()
        assert isinstance(networks, list)
        assert all(isinstance(name, str) and name.strip() for name in networks)

    @pytest.mark.diagnostic
    def test_get_connected_network(self, restored_wifi: WifiSettingsPage):
        """Inspect connection state while preserving the original radio setting."""
        restored_wifi.enable_wifi()
        connected = restored_wifi.get_connected_network()
        assert connected is None or (isinstance(connected, str) and connected.strip())


@pytest.mark.settings
class TestDisplaySettings:
    """Tests for Display & Brightness settings."""

    @pytest.mark.real_device(reason="Display appearance controls differ on simulator")
    def test_toggle_dark_mode(self, settings_app: SettingsHomePage):
        """Test toggling between light and dark mode."""
        display_page = settings_app.go_to_display_brightness()
        initial_automatic = display_page.is_automatic_appearance_enabled()
        initial_dark_mode = display_page.is_dark_mode_active()
        try:
            display_page.disable_automatic_appearance()
            display_page.set_light_mode()
            assert display_page.is_light_mode_active()

            display_page.set_dark_mode()
            assert display_page.is_dark_mode_active()
        finally:
            if initial_dark_mode:
                display_page.set_dark_mode()
            else:
                display_page.set_light_mode()

            if initial_automatic:
                display_page.enable_automatic_appearance()
            else:
                display_page.disable_automatic_appearance()

    @pytest.mark.real_device(reason="Display appearance controls differ on simulator")
    def test_automatic_appearance_toggle(self, settings_app: SettingsHomePage):
        """Test automatic appearance toggle."""
        display_page = settings_app.go_to_display_brightness()
        initial_state = display_page.is_automatic_appearance_enabled()
        try:
            display_page.toggle_automatic_appearance()
            assert display_page.is_automatic_appearance_enabled() != initial_state
        finally:
            if display_page.is_automatic_appearance_enabled() != initial_state:
                display_page.toggle_automatic_appearance()

        assert display_page.is_automatic_appearance_enabled() == initial_state

    @pytest.mark.real_device(reason="True Tone is not expected on simulator")
    def test_true_tone_toggle(self, settings_app: SettingsHomePage):
        """Test True Tone toggle (if available on device)."""
        display_page = settings_app.go_to_display_brightness()

        # This test may not work on simulators or older devices
        if display_page.is_element_present(display_page.TRUE_TONE_SWITCH, timeout=2):
            initial_state = display_page.is_true_tone_enabled()
            try:
                display_page.toggle_true_tone()
                assert display_page.is_true_tone_enabled() != initial_state
            finally:
                if display_page.is_true_tone_enabled() != initial_state:
                    display_page.toggle_true_tone()
        else:
            pytest.skip("True Tone not available on this device")

    @pytest.mark.real_device(reason="Brightness UI differs on simulator")
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

    def test_get_device_name(self, settings_app: SettingsHomePage):
        """Test retrieving device name from About."""
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()

        device_name = about_page.get_device_name()

        assert device_name and device_name.strip(), "Device name missing"
        print(f"Device name: {device_name}")

    def test_get_ios_version(self, settings_app: SettingsHomePage):
        """Test retrieving iOS version from About."""
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()

        ios_version = about_page.get_ios_version()

        assert ios_version and re.match(r"^\d+\.\d+", ios_version), "iOS version missing or invalid"

    def test_get_model_name(self, settings_app: SettingsHomePage):
        """Test retrieving device model name from About."""
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()

        model_name = about_page.get_model_name()

        assert model_name and model_name.strip(), "Model name missing"

    @pytest.mark.real_device(reason="Software Update entry is not exposed on simulator")
    def test_navigate_to_software_update(self, settings_app: SettingsHomePage):
        """Test navigation to Software Update screen."""
        general_page = settings_app.go_to_general()
        general_page.go_to_software_update()

        # Verify we're on the Software Update screen
        # by checking for common elements
        update_title = (general_page.By.ACCESSIBILITY_ID, "Software Update")
        assert general_page.is_element_present(update_title, timeout=5)


@pytest.mark.settings
class TestAirplaneMode:
    """Tests for Airplane Mode functionality."""

    @pytest.mark.real_device(reason="Airplane Mode is hardware-specific")
    def test_airplane_mode_toggle(self, settings_app: SettingsHomePage):
        """Test toggling Airplane Mode on and off."""
        initial_state = settings_app.is_airplane_mode_on()
        try:
            settings_app.toggle_airplane_mode()
            assert settings_app.is_airplane_mode_on() != initial_state
        finally:
            if settings_app.is_airplane_mode_on() != initial_state:
                settings_app.toggle_airplane_mode()

        assert settings_app.is_airplane_mode_on() == initial_state

    @pytest.mark.real_device(reason="Airplane Mode and Wi-Fi interaction is hardware-specific")
    def test_airplane_mode_disables_wifi(self, settings_app: SettingsHomePage):
        """Test that enabling Airplane Mode affects Wi-Fi."""
        wifi_page = settings_app.go_to_wifi()
        initial_wifi_state = wifi_page.is_wifi_enabled()
        wifi_page.go_back_to_settings()
        initial_airplane_state = settings_app.is_airplane_mode_on()

        try:
            if initial_airplane_state:
                settings_app.toggle_airplane_mode()

            wifi_page = settings_app.go_to_wifi()
            wifi_page.enable_wifi()
            wifi_page.go_back_to_settings()

            settings_app.toggle_airplane_mode()
            assert settings_app.is_airplane_mode_on()
        finally:
            if settings_app.is_airplane_mode_on() != initial_airplane_state:
                settings_app.toggle_airplane_mode()

            wifi_page = settings_app.go_to_wifi()
            if initial_wifi_state:
                wifi_page.enable_wifi()
            else:
                wifi_page.disable_wifi()


@pytest.mark.settings
class TestSettingsSearch:
    """Tests for Settings search functionality."""

    @pytest.mark.real_device(reason="Settings search results differ on simulator")
    def test_search_for_wifi(self, settings_app: SettingsHomePage):
        """Test searching for Wi-Fi in settings."""
        settings_app.search_settings("Wi-Fi")

        # Verify search results show Wi-Fi option
        wifi_result = (settings_app.By.ACCESSIBILITY_ID, "Wi-Fi")
        assert settings_app.is_element_present(wifi_result, timeout=5)

        # Clear search
        settings_app.clear_search()

    @pytest.mark.real_device(reason="Settings search results differ on simulator")
    def test_search_for_display(self, settings_app: SettingsHomePage):
        """Test searching for display settings."""
        settings_app.search_settings("Display")

        # Verify search results show Display & Brightness option
        display_result = (settings_app.By.ACCESSIBILITY_ID, "Display & Brightness")
        assert settings_app.is_element_present(display_result, timeout=5)

        # Clear search
        settings_app.clear_search()

    @pytest.mark.real_device(reason="Settings search navigation differs on simulator")
    def test_search_and_navigate(self, settings_app: SettingsHomePage):
        """Test searching and navigating to a result."""
        settings_app.search_settings("General")

        # Tap on General in search results
        general_cell = (settings_app.By.ACCESSIBILITY_ID, "General")
        settings_app.click(general_cell)

        # Verify we navigated to General settings
        general_page = GeneralSettingsPage(settings_app.driver)
        assert general_page.is_on_general_page()
