"""Known iOS system prompts and the button each one is answered with."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException

Permission = Literal["allow", "deny"]

DONT_ALLOW = "Don’t Allow"


@dataclass(frozen=True)
class PromptAnswer:
    """Buttons for one prompt; ``allow`` is None when the answer never varies."""

    deny: str
    allow: str | None = None

    def button(self, permission: Permission) -> str:
        """Return the button label for the requested permission decision."""
        return self.allow if permission == "allow" and self.allow else self.deny


def _permission_prompts(app: str) -> dict[str, PromptAnswer]:
    """Standard privacy prompts that iOS shows for a system app."""
    return {
        f"Allow “{app}” to use your location?": PromptAnswer(DONT_ALLOW, "Allow While Using App"),
        f"“{app}” Would Like to Send You Notifications": PromptAnswer(DONT_ALLOW),
        f"Allow “{app}” to access your contacts?": PromptAnswer(DONT_ALLOW),
    }


# Keyed by visible title. iOS 27 "staged" prompts can surface over any app, so every page
# recognizes every app's prompts. Add new prompts here; unknown alerts fail the run.
KNOWN_PROMPTS: dict[str, PromptAnswer] = {
    **_permission_prompts("Calendar"),
    **_permission_prompts("Maps"),
    "Allow widgets from “Maps” to use your location?": PromptAnswer(DONT_ALLOW, "Allow"),
    "Getting There Safely": PromptAnswer("OK"),
}

_STRAIGHT_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})


def _normalize(text: str) -> str:
    """Compare titles and labels regardless of curly or straight quotes."""
    return text.translate(_STRAIGHT_QUOTES)


_ANSWERS = {_normalize(title): answer for title, answer in KNOWN_PROMPTS.items()}


def _text(element: WebElement, attribute: str) -> str:
    """Read a string attribute; Appium types attributes as ``str | dict``."""
    value = element.get_attribute(attribute)
    return value if isinstance(value, str) else ""


def answer_system_prompt(driver: WebDriver, context: str, permission: Permission = "deny") -> bool:
    """Answer the first visible system alert if it is a known prompt.

    Args:
        driver: Active Appium session.
        context: App under test, used in failure messages.
        permission: Decision for prompts that offer one; others use their fixed button.

    Returns:
        True if a prompt was answered, False if no alert is showing (or it is animating away).

    Raises:
        AssertionError: If the visible alert is unknown, or lacks its expected button.
    """
    for alert in driver.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeAlert"):
        try:
            if not alert.is_displayed():
                continue
            # iOS 27 permission alerts name themselves by service ID
            # (kTCCServiceAddressBook-staged-alert); the label is the visible title.
            title = _text(alert, "label") or _text(alert, "name")
            answer = _ANSWERS.get(_normalize(title))
            if answer is None:
                raise AssertionError(f"Unexpected {context} alert: {title}")
            wanted = _normalize(answer.button(permission))
            for button in alert.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeButton"):
                if _normalize(_text(button, "label")) == wanted:
                    button.click()
                    return True
            raise AssertionError(f"Known {context} prompt has no '{wanted}' button: {title}")
        except StaleElementReferenceException:
            # The alert is animating away; check again on the next poll.
            return False
    return False
