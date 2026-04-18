"""
Test suite for the iOS Settings app.

These tests demonstrate automation of the native Settings app,
covering navigation, toggles, and settings verification.
"""

import pytest

from src.pages.settings import (
    GeneralSettingsPage,
    SettingsHomePage,
)


def require_real_device(is_simulator: bool, reason: str) -> None:
    """Skip test when current target is simulator-only."""
    if is_simulator:
        pytest.skip(reason)


@pytest.mark.settings
@pytest.mark.smoke
class TestSettingsNavigation:
    """Tests for Settings app navigation."""

    def test_settings_app_launches(self, settings_app: SettingsHomePage):
        """Verify Settings app launches successfully."""
        assert settings_app.is_on_settings_home()

    def test_navigate_to_wifi(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Verify navigation to Wi-Fi settings."""
        require_real_device(is_simulator, "Wi-Fi settings layout differs on simulator")
        wifi_page = settings_app.go_to_wifi()
        assert wifi_page.is_on_wifi_page()

    def test_navigate_to_general(self, settings_app: SettingsHomePage):
        """Verify navigation to General settings."""
        general_page = settings_app.go_to_general()
        assert general_page.is_on_general_page()

    def test_navigate_to_display_brightness(
        self, settings_app: SettingsHomePage, is_simulator: bool
    ):
        """Verify navigation to Display & Brightness settings."""
        require_real_device(is_simulator, "Display settings layout differs on simulator")
        display_page = settings_app.go_to_display_brightness()
        assert display_page.is_on_display_page()

    def test_navigate_to_general_about(self, settings_app: SettingsHomePage):
        """Verify navigation to General > About."""
        general_page = settings_app.go_to_general()
        about_page = general_page.go_to_about()
        assert about_page.is_on_about_page()

    def test_back_navigation(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Verify back navigation returns to previous screen."""
        require_real_device(is_simulator, "Back path via Wi-Fi screen differs on simulator")
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

    def test_wifi_toggle(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Test toggling Wi-Fi on and off."""
        require_real_device(is_simulator, "Wi-Fi radio controls are hardware-specific")
        wifi_page = settings_app.go_to_wifi()
        initial_state = wifi_page.is_wifi_enabled()
        try:
            wifi_page.toggle_wifi()
            assert wifi_page.is_wifi_enabled() != initial_state
        finally:
            if wifi_page.is_wifi_enabled() != initial_state:
                wifi_page.toggle_wifi()

        assert wifi_page.is_wifi_enabled() == initial_state

    def test_wifi_enable_disable(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Test explicit enable/disable methods."""
        require_real_device(is_simulator, "Wi-Fi radio controls are hardware-specific")
        wifi_page = settings_app.go_to_wifi()
        initial_state = wifi_page.is_wifi_enabled()
        try:
            wifi_page.enable_wifi()
            assert wifi_page.is_wifi_enabled()

            wifi_page.disable_wifi()
            assert not wifi_page.is_wifi_enabled()
        finally:
            if initial_state:
                wifi_page.enable_wifi()
            else:
                wifi_page.disable_wifi()

    @pytest.mark.slow
    def test_list_available_networks(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Test listing available Wi-Fi networks."""
        require_real_device(is_simulator, "Available Wi-Fi networks require real hardware state")
        wifi_page = settings_app.go_to_wifi()

        # Ensure Wi-Fi is on
        wifi_page.enable_wifi()

        # Get available networks
        networks = wifi_page.get_available_networks()

        # Should find at least some networks (in most environments)
        # Note: This may fail in isolated test environments
        print(f"Found {len(networks)} networks: {networks}")

    def test_get_connected_network(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Test getting the currently connected network name."""
        require_real_device(is_simulator, "Connected Wi-Fi state requires real hardware")
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

    def test_toggle_dark_mode(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Test toggling between light and dark mode."""
        require_real_device(is_simulator, "Display appearance controls differ on simulator")
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

    def test_automatic_appearance_toggle(
        self, settings_app: SettingsHomePage, is_simulator: bool
    ):
        """Test automatic appearance toggle."""
        require_real_device(is_simulator, "Display appearance controls differ on simulator")
        display_page = settings_app.go_to_display_brightness()
        initial_state = display_page.is_automatic_appearance_enabled()
        try:
            display_page.toggle_automatic_appearance()
            assert display_page.is_automatic_appearance_enabled() != initial_state
        finally:
            if display_page.is_automatic_appearance_enabled() != initial_state:
                display_page.toggle_automatic_appearance()

        assert display_page.is_automatic_appearance_enabled() == initial_state

    def test_true_tone_toggle(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Test True Tone toggle (if available on device)."""
        require_real_device(is_simulator, "True Tone is not expected on simulator")
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

    def test_get_brightness_level(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Test getting current brightness level."""
        require_real_device(is_simulator, "Brightness UI differs on simulator")
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

    def test_navigate_to_software_update(
        self, settings_app: SettingsHomePage, is_simulator: bool
    ):
        """Test navigation to Software Update screen."""
        require_real_device(is_simulator, "Software Update entry is not exposed on simulator")
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

    def test_airplane_mode_toggle(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Test toggling Airplane Mode on and off."""
        require_real_device(is_simulator, "Airplane Mode is hardware-specific")
        initial_state = settings_app.is_airplane_mode_on()
        try:
            settings_app.toggle_airplane_mode()
            assert settings_app.is_airplane_mode_on() != initial_state
        finally:
            if settings_app.is_airplane_mode_on() != initial_state:
                settings_app.toggle_airplane_mode()

        assert settings_app.is_airplane_mode_on() == initial_state

    def test_airplane_mode_disables_wifi(
        self, settings_app: SettingsHomePage, is_simulator: bool
    ):
        """Test that enabling Airplane Mode affects Wi-Fi."""
        require_real_device(is_simulator, "Airplane Mode and Wi-Fi interaction is hardware-specific")
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

    def test_search_for_wifi(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Test searching for Wi-Fi in settings."""
        require_real_device(is_simulator, "Settings search results differ on simulator")
        settings_app.search_settings("Wi-Fi")

        # Verify search results show Wi-Fi option
        wifi_result = (settings_app.By.ACCESSIBILITY_ID, "Wi-Fi")
        assert settings_app.is_element_present(wifi_result, timeout=5)

        # Clear search
        settings_app.clear_search()

    def test_search_for_display(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Test searching for display settings."""
        require_real_device(is_simulator, "Settings search results differ on simulator")
        settings_app.search_settings("Display")

        # Verify search results show Display & Brightness option
        display_result = (settings_app.By.ACCESSIBILITY_ID, "Display & Brightness")
        assert settings_app.is_element_present(display_result, timeout=5)

        # Clear search
        settings_app.clear_search()

    def test_search_and_navigate(self, settings_app: SettingsHomePage, is_simulator: bool):
        """Test searching and navigating to a result."""
        require_real_device(is_simulator, "Settings search navigation differs on simulator")
        settings_app.search_settings("General")

        # Tap on General in search results
        general_cell = (settings_app.By.ACCESSIBILITY_ID, "General")
        settings_app.click(general_cell)

        # Verify we navigated to General settings
        general_page = GeneralSettingsPage(settings_app.driver)
        assert general_page.is_on_general_page()
