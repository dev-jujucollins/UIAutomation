"""Known system prompts are answered by visible title; anything else fails the run."""

from unittest.mock import MagicMock

import pytest
from selenium.common.exceptions import StaleElementReferenceException

from uiautomation.pages.system_prompts import KNOWN_PROMPTS, answer_system_prompt

BUTTONS = ("Don’t Allow", "Allow While Using App", "Allow", "OK")


def _button(label: str) -> MagicMock:
    button = MagicMock()
    button.get_attribute.side_effect = {"label": label}.get
    return button


def _alert(label: str, *, name: str | None = None, buttons=BUTTONS, visible=True) -> MagicMock:
    alert = MagicMock()
    alert.is_displayed.return_value = visible
    alert.get_attribute.side_effect = {"label": label, "name": name or label}.get
    alert.find_elements.return_value = [_button(text) for text in buttons]
    return alert


def _driver(*alerts: MagicMock) -> MagicMock:
    driver = MagicMock()
    driver.find_elements.return_value = list(alerts)
    return driver


def _clicked(alert: MagicMock) -> list[str]:
    return [
        button.get_attribute("label")
        for button in alert.find_elements.return_value
        if button.click.called
    ]


@pytest.mark.parametrize(
    "title, permission, button",
    [
        ("Allow “Maps” to use your location?", "allow", "Allow While Using App"),
        ("Allow “Maps” to use your location?", "deny", "Don’t Allow"),
        ("Allow widgets from “Maps” to use your location?", "allow", "Allow"),
        ("Allow widgets from “Maps” to use your location?", "deny", "Don’t Allow"),
        ("Allow “Calendar” to use your location?", "deny", "Don’t Allow"),
        ("“Calendar” Would Like to Send You Notifications", "allow", "Don’t Allow"),
        ("Allow “Maps” to access your contacts?", "allow", "Don’t Allow"),
        ("Getting There Safely", "deny", "OK"),
    ],
)
def test_known_prompt_uses_permission_or_fixed_button(title: str, permission, button: str) -> None:
    alert = _alert(title)
    assert answer_system_prompt(_driver(alert), "Maps", permission) is True
    assert _clicked(alert) == [button]


def test_every_known_prompt_has_a_deny_button() -> None:
    assert all(answer.deny for answer in KNOWN_PROMPTS.values())


def test_ios_27_service_id_name_is_ignored_for_visible_label() -> None:
    alert = _alert(
        "Allow “Calendar” to access your contacts?", name="kTCCServiceAddressBook-staged-alert"
    )
    assert answer_system_prompt(_driver(alert), "Calendar") is True
    assert _clicked(alert) == ["Don’t Allow"]


def test_straight_quotes_match_curly_titles_and_buttons() -> None:
    alert = _alert('"Calendar" Would Like to Send You Notifications', buttons=("Don't Allow",))
    assert answer_system_prompt(_driver(alert), "Calendar") is True
    assert _clicked(alert) == ["Don't Allow"]


@pytest.mark.parametrize("title", ["Allow “Calendar” to access your photos?", ""])
def test_unknown_alert_fails_without_tapping(title: str) -> None:
    alert = _alert(title)
    with pytest.raises(AssertionError, match="Unexpected Calendar alert"):
        answer_system_prompt(_driver(alert), "Calendar")
    assert _clicked(alert) == []


def test_known_prompt_without_expected_button_fails() -> None:
    alert = _alert("Getting There Safely", buttons=("Cancel",))
    with pytest.raises(AssertionError, match="has no 'OK' button"):
        answer_system_prompt(_driver(alert), "Maps")
    assert _clicked(alert) == []


def test_hidden_alerts_and_no_alerts_are_not_answered() -> None:
    hidden = _alert("Getting There Safely", visible=False)
    assert answer_system_prompt(_driver(hidden), "Maps") is False
    assert answer_system_prompt(_driver(), "Maps") is False


def test_alert_animating_away_is_retried_later() -> None:
    alert = _alert("Getting There Safely")
    alert.get_attribute.side_effect = StaleElementReferenceException()
    assert answer_system_prompt(_driver(alert), "Maps") is False
