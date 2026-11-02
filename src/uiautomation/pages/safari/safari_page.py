"""Safari browser chrome and web content, observed on the English iOS 27.2 simulator."""

from __future__ import annotations

from typing import Literal

from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException

from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.utils.locators import predicate_literal

from ..base_page import BasePage
from ..system_prompts import answer_system_prompt

WebKind = Literal["StaticText", "Link", "Button", "Other", "TextField"]


class SafariPage(BasePage):
    """Open URLs and read or drive a page through its accessibility tree.

    Web elements are exposed by their accessible names: link and heading text,
    ``aria-label`` for inputs, and button text.
    """

    # Address bar while showing a page, and while editing.
    ADDRESS_BAR = (BasePage.By.ACCESSIBILITY_ID, "TabBarItemTitle")
    ADDRESS_FIELD = (BasePage.By.ACCESSIBILITY_ID, "URL")
    BACK_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "BackButton")
    FORWARD_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "ForwardButton")
    TABS_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "TabOverviewButton")
    # First-launch notices, matched by their text so a generic "Not Now" is never tapped.
    ICLOUD_TOPICS_TEXT = (BasePage.By.ACCESSIBILITY_ID, "Include topics from other devices")
    ICLOUD_TOPICS_DECLINE = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND name == 'Not Now'",
    )
    SUGGESTIONS_NOTICE = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeTextView' AND name BEGINSWITH 'Safari search now shows'",
    )
    SUGGESTIONS_CONTINUE = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND name == 'Continue'",
    )
    LAUNCH_TIMEOUT = 30
    PAGE_LOAD_TIMEOUT = 30

    HEALTH_LOCATORS = ("TABS_BUTTON",)

    def _visible(self, locator: tuple[str, str]) -> WebElement | None:
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return element
            except StaleElementReferenceException:
                continue
        return None

    def _dismiss_known_notice(self) -> bool:
        """Answer one first-launch notice; True when something was tapped."""
        if answer_system_prompt(self.driver, "Safari"):
            return True
        for text, button in (
            (self.ICLOUD_TOPICS_TEXT, self.ICLOUD_TOPICS_DECLINE),
            (self.SUGGESTIONS_NOTICE, self.SUGGESTIONS_CONTINUE),
        ):
            if self._visible(text):
                control = self._visible(button)
                if control is None:
                    raise AssertionError(f"Known Safari notice has no dismiss control: {text[1]}")
                control.click()
                return True
        return False

    def wait_until_ready(self) -> None:
        """Get past first-launch notices to a usable address bar."""

        def ready(_: WebDriver) -> bool:
            try:
                if self._dismiss_known_notice():
                    return False
                return bool(self._visible(self.ADDRESS_BAR) or self._visible(self.ADDRESS_FIELD))
            except StaleElementReferenceException:
                return False

        self._get_wait(self.LAUNCH_TIMEOUT).until(ready, "Safari address bar not ready")

    def open_url(self, url: str, loaded: tuple[str, str]) -> None:
        """Open a URL in Safari and wait for an element of the loaded page.

        A deep link, not typing: the address bar autocompletes from history, so typing
        ``http://host/`` after visiting ``http://host/page.html`` would load the latter.
        """
        self.driver.execute_script(
            "mobile: deepLink", {"url": url, "bundleId": SystemApps.SAFARI.value}
        )
        self.wait_for_visible(loaded, timeout=self.PAGE_LOAD_TIMEOUT)

    def host(self) -> str:
        """Host shown in the address bar, without Safari's left-to-right mark."""
        value = self.find_element(self.ADDRESS_BAR).get_attribute("value")
        return str(value or "").strip("‎‏ ")

    @classmethod
    def web(cls, kind: WebKind, label: str) -> tuple[str, str]:
        """A web element by type and exact accessible label.

        Text and headings are StaticText, links are Link, landmarks such as
        ``<nav aria-label>`` are Other, inputs are TextField (named by aria-label).
        """
        return (
            cls.By.IOS_PREDICATE,
            f"type == 'XCUIElementType{kind}' AND label == {predicate_literal(label)}",
        )

    @classmethod
    def text(cls, label: str) -> tuple[str, str]:
        return cls.web("StaticText", label)

    def wait_for(self, locator: tuple[str, str]) -> WebElement:
        return self.wait_for_visible(locator, timeout=self.PAGE_LOAD_TIMEOUT)

    def wait_for_text(self, label: str) -> WebElement:
        return self.wait_for(self.text(label))

    def is_showing(self, locator: tuple[str, str]) -> bool:
        return bool(self._visible(locator))

    def tap(self, kind: WebKind, label: str) -> None:
        """Tap a web link, button, or other element by its accessible label."""
        self.click(self.web(kind, label))

    def fill(self, field_label: str, value: str) -> None:
        """Type into a web input identified by its accessible label (aria-label)."""
        self.send_keys(self.web("TextField", field_label), value, clear_first=True)

    def go_back(self, loaded: tuple[str, str]) -> None:
        """Use Safari's Back button and wait for an element of the previous page."""
        self.click(self.BACK_BUTTON)
        self.wait_for(loaded)
