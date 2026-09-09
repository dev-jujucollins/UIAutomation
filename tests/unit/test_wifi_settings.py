"""Tests for wifi settings."""

from unittest.mock import MagicMock

from uiautomation.pages.settings.wifi_settings import WifiSettingsPage


def test_get_connected_network_requires_selected_state() -> None:
    """Only a selected Wi-Fi cell should be reported as connected."""
    page = WifiSettingsPage(MagicMock())
    page.is_wifi_enabled = MagicMock(return_value=True)

    first_cell = MagicMock()
    first_cell.get_attribute.side_effect = lambda name: {
        "selected": "false",
        "value": "0",
        "label": "CoffeeShop, Secure network, Signal strength 3 of 3 bars",
    }.get(name)
    first_cell.find_element.side_effect = Exception("not selected")

    second_cell = MagicMock()
    second_cell.get_attribute.side_effect = lambda name: {
        "selected": "true",
        "value": "1",
        "label": "OfficeWiFi, Secure network, Signal strength 3 of 3 bars",
    }.get(name)

    page.find_elements = MagicMock(return_value=[first_cell, second_cell])

    assert page.get_connected_network() == "OfficeWiFi"


def test_open_network_details_clicks_info_button_inside_target_cell() -> None:
    """Network details should use the target cell's info button, not the row tap."""
    page = WifiSettingsPage(MagicMock())
    page.scroll_to_element = MagicMock(return_value=True)

    info_button = MagicMock()
    cell = MagicMock()
    cell.find_element.return_value = info_button
    page.find_element = MagicMock(return_value=cell)

    assert page.open_network_details("OfficeWiFi") is True
    info_button.click.assert_called_once_with()
