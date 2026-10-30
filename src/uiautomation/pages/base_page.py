"""
Base Page Object class for iOS automation.
"""

from typing import cast

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait


class BasePage:
    """
    Base class for all page objects.

    Provides common methods for element interaction, waiting, and navigation
    that are shared across all page objects.
    """

    # Default timeout for explicit waits
    DEFAULT_TIMEOUT = 10

    # Names of locators that must exist once this page is ready. `uiautomation locators`
    # checks them all at once, so renamed controls show up before they break tests.
    HEALTH_LOCATORS: tuple[str, ...] = ()

    # Common locator strategies
    class By:
        """Locator strategy shortcuts."""

        ACCESSIBILITY_ID = AppiumBy.ACCESSIBILITY_ID
        CLASS_NAME = AppiumBy.CLASS_NAME
        XPATH = AppiumBy.XPATH
        IOS_PREDICATE = AppiumBy.IOS_PREDICATE
        IOS_CLASS_CHAIN = AppiumBy.IOS_CLASS_CHAIN
        NAME = AppiumBy.NAME

    def __init__(self, driver: WebDriver):
        """
        Initialize base page.

        Args:
            driver: Appium WebDriver instance.
        """
        self.driver = driver
        self._wait = WebDriverWait(driver, self.DEFAULT_TIMEOUT)

    # -------------------------------------------------------------------------
    # Element Finding Methods
    # -------------------------------------------------------------------------

    def find_element(self, locator: tuple[str, str], timeout: int | None = None) -> WebElement:
        """
        Find an element with explicit wait.

        Args:
            locator: Tuple of (By strategy, locator value).
            timeout: Optional timeout override.

        Returns:
            The found WebElement.

        Raises:
            TimeoutException: If element not found within timeout.
        """
        wait = self._get_wait(timeout)
        return cast(
            WebElement, wait.until(expected_conditions.presence_of_element_located(locator))
        )

    def find_elements(
        self, locator: tuple[str, str], timeout: int | None = None
    ) -> list[WebElement]:
        """
        Find multiple elements.

        Args:
            locator: Tuple of (By strategy, locator value).
            timeout: Optional timeout override.

        Returns:
            List of found WebElements (empty if none found).
        """
        try:
            wait = self._get_wait(timeout)
            wait.until(expected_conditions.presence_of_element_located(locator))
            return self.driver.find_elements(*locator)
        except TimeoutException:
            return []

    # -------------------------------------------------------------------------
    # Element Interaction Methods
    # -------------------------------------------------------------------------

    def click(self, locator: tuple[str, str], timeout: int | None = None) -> None:
        """
        Click an element.

        Args:
            locator: Tuple of (By strategy, locator value).
            timeout: Optional timeout override.
        """
        element = self.wait_for_clickable(locator, timeout)
        element.click()

    def send_keys(
        self,
        locator: tuple[str, str],
        text: str,
        clear_first: bool = True,
        timeout: int | None = None,
    ) -> None:
        """
        Send keys to an element.

        Args:
            locator: Tuple of (By strategy, locator value).
            text: Text to enter.
            clear_first: Whether to clear existing text first.
            timeout: Optional timeout override.
        """
        element = self.wait_for_clickable(locator, timeout)
        if clear_first:
            element.clear()
        element.send_keys(text)

    def get_text(self, locator: tuple[str, str], timeout: int | None = None) -> str:
        """
        Get text from an element.

        Args:
            locator: Tuple of (By strategy, locator value).
            timeout: Optional timeout override.

        Returns:
            The element's text content.
        """
        element = self.find_element(locator, timeout)
        return element.text

    def set_switch_state(
        self,
        locator: tuple[str, str],
        enabled: bool,
        *,
        click_locator: tuple[str, str] | None = None,
        timeout: int | None = None,
    ) -> None:
        """Set a switch once and wait until a fresh element confirms its state.

        Args:
            locator: Switch whose value reports its state.
            enabled: Desired switch state.
            click_locator: Optional nested control to tap instead of the state element.
            timeout: Optional timeout override.

        Raises:
            TimeoutException: If the requested state cannot be confirmed.
        """
        expected = "1" if enabled else "0"
        clicked = False

        def ready(driver: WebDriver) -> bool:
            nonlocal clicked
            try:
                switch = driver.find_element(*locator)
                value = switch.get_attribute("value")
                if value == expected:
                    return True
                if clicked or value not in ("0", "1"):
                    return False
                control = driver.find_element(*click_locator) if click_locator else switch
                if not control.is_displayed() or not control.is_enabled():
                    return False
                # A stale response may arrive after a successful tap. Never toggle
                # twice while waiting for an asynchronously refreshed switch value.
                clicked = True
                control.click()
            except StaleElementReferenceException:
                return False
            return False

        self._get_wait(timeout).until(
            ready, message=f"Switch {locator!r} did not reach value {expected!r}"
        )

    def wait_for_attribute(
        self,
        locator: tuple[str, str],
        attribute: str,
        value: str,
        timeout: int | None = None,
    ) -> None:
        """Wait for an attribute value, re-finding controls during UI refreshes.

        Args:
            locator: Element to check.
            attribute: Attribute name.
            value: Required attribute value.
            timeout: Optional timeout override.
        """

        def matches(driver: WebDriver) -> bool:
            try:
                return driver.find_element(*locator).get_attribute(attribute) == value
            except StaleElementReferenceException:
                return False

        self._get_wait(timeout).until(
            matches, message=f"Element {locator!r} did not reach {attribute}={value!r}"
        )

    def get_attribute(
        self, locator: tuple[str, str], attribute: str, timeout: int | None = None
    ) -> str | None:
        """
        Get an attribute value from an element.

        Args:
            locator: Tuple of (By strategy, locator value).
            attribute: Attribute name.
            timeout: Optional timeout override.

        Returns:
            The attribute value or None.
        """
        element = self.find_element(locator, timeout)
        value = element.get_attribute(attribute)
        return value if isinstance(value, str) else None

    # -------------------------------------------------------------------------
    # Wait Methods
    # -------------------------------------------------------------------------

    def wait_for_visible(self, locator: tuple[str, str], timeout: int | None = None) -> WebElement:
        """
        Wait for element to be visible.

        Args:
            locator: Tuple of (By strategy, locator value).
            timeout: Optional timeout override.

        Returns:
            The visible WebElement.
        """
        wait = self._get_wait(timeout)
        return cast(
            WebElement, wait.until(expected_conditions.visibility_of_element_located(locator))
        )

    def wait_for_clickable(
        self, locator: tuple[str, str], timeout: int | None = None
    ) -> WebElement:
        """
        Wait for element to be clickable.

        Args:
            locator: Tuple of (By strategy, locator value).
            timeout: Optional timeout override.

        Returns:
            The clickable WebElement.
        """
        wait = self._get_wait(timeout)
        return cast(WebElement, wait.until(expected_conditions.element_to_be_clickable(locator)))

    def wait_for_invisible(self, locator: tuple[str, str], timeout: int | None = None) -> bool:
        """
        Wait for element to become invisible.

        Args:
            locator: Tuple of (By strategy, locator value).
            timeout: Optional timeout override.

        Returns:
            True if element is invisible.
        """
        wait = self._get_wait(timeout)
        return bool(wait.until(expected_conditions.invisibility_of_element_located(locator)))

    def wait_for_text_present(
        self, locator: tuple[str, str], text: str, timeout: int | None = None
    ) -> bool:
        """
        Wait for specific text to be present in an element.

        Args:
            locator: Tuple of (By strategy, locator value).
            text: Text to wait for.
            timeout: Optional timeout override.

        Returns:
            True if text is present.
        """
        wait = self._get_wait(timeout)
        return wait.until(expected_conditions.text_to_be_present_in_element(locator, text))

    # -------------------------------------------------------------------------
    # State Check Methods
    # -------------------------------------------------------------------------

    def is_element_present(self, locator: tuple[str, str], timeout: int = 2) -> bool:
        """
        Check if element is present in DOM.

        Args:
            locator: Tuple of (By strategy, locator value).
            timeout: Short timeout for presence check.

        Returns:
            True if element is present.
        """
        try:
            self.find_element(locator, timeout)
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def is_element_visible(self, locator: tuple[str, str], timeout: int = 2) -> bool:
        """
        Check if element is visible.

        Args:
            locator: Tuple of (By strategy, locator value).
            timeout: Short timeout for visibility check.

        Returns:
            True if element is visible.
        """
        try:
            self.wait_for_visible(locator, timeout)
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def is_element_enabled(self, locator: tuple[str, str]) -> bool:
        """
        Check if element is enabled.

        Args:
            locator: Tuple of (By strategy, locator value).

        Returns:
            True if element is enabled.
        """
        try:
            element = self.find_element(locator, timeout=2)
            return element.is_enabled()
        except (TimeoutException, NoSuchElementException):
            return False

    # -------------------------------------------------------------------------
    # Scroll Methods
    # -------------------------------------------------------------------------

    def scroll_down(self) -> None:
        """Scroll down on the current screen."""
        self.driver.execute_script("mobile: scroll", {"direction": "down"})

    def scroll_up(self) -> None:
        """Scroll up on the current screen."""
        self.driver.execute_script("mobile: scroll", {"direction": "up"})

    def scroll_to_element(
        self, locator: tuple[str, str], max_scrolls: int = 5, direction: str = "down"
    ) -> WebElement | None:
        """
        Scroll until element is found.

        Args:
            locator: Tuple of (By strategy, locator value).
            max_scrolls: Maximum scroll attempts.
            direction: Scroll direction ("up" or "down").

        Returns:
            The found element or None if not found.
        """
        if max_scrolls < 0:
            raise ValueError("max_scrolls must be non-negative")
        if direction not in ("up", "down"):
            raise ValueError("direction must be 'up' or 'down'")
        for attempt in range(max_scrolls + 1):
            if self.is_element_visible(locator, timeout=1):
                return self.find_element(locator)

            if attempt == max_scrolls:
                break

            if direction == "down":
                self.scroll_down()
            else:
                self.scroll_up()

        return None

    def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500
    ) -> None:
        """
        Perform a swipe gesture.

        Args:
            start_x: Starting X coordinate.
            start_y: Starting Y coordinate.
            end_x: Ending X coordinate.
            end_y: Ending Y coordinate.
            duration: Swipe duration in milliseconds.
        """
        self.driver.execute_script(
            "mobile: dragFromToForDuration",
            {
                "fromX": start_x,
                "fromY": start_y,
                "toX": end_x,
                "toY": end_y,
                "duration": duration / 1000,  # Convert to seconds
            },
        )

    # -------------------------------------------------------------------------
    # Navigation Methods
    # -------------------------------------------------------------------------

    def tap_back_button(self) -> None:
        """Tap the navigation back button.

        Raises:
            TimeoutException: If no back button is visible.
        """
        self.click((self.By.ACCESSIBILITY_ID, "BackButton"))

    # -------------------------------------------------------------------------
    # Screenshot Methods
    # -------------------------------------------------------------------------

    def take_screenshot(self, filename: str) -> str:
        """
        Take a screenshot.

        Args:
            filename: Path to save screenshot.

        Returns:
            The screenshot file path.
        """
        self.driver.save_screenshot(filename)
        return filename

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _get_wait(self, timeout: int | None) -> WebDriverWait:
        """
        Get a WebDriverWait instance.

        Args:
            timeout: Optional timeout. Uses default if None.

        Returns:
            WebDriverWait instance.
        """
        if timeout is None:
            return self._wait
        return WebDriverWait(self.driver, timeout)

    def missing_health_locators(self) -> list[str]:
        """Describe each health locator that matches nothing on the current screen."""
        missing = []
        for name in self.HEALTH_LOCATORS:
            by, value = getattr(self, name)
            if not self.driver.find_elements(by, value):
                missing.append(f"{type(self).__name__}.{name} ({by}: {value})")
        return missing

    def get_page_source(self) -> str:
        """
        Get the current page source (XML).

        Returns:
            Page source as string.
        """
        return self.driver.page_source

    def get_screen_size(self) -> dict:
        """
        Get the screen dimensions.

        Returns:
            Dict with 'width' and 'height' keys.
        """
        return self.driver.get_window_size()
