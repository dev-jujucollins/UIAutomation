"""
Base Page Object class for iOS automation.
"""

from typing import List, Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class BasePage:
    """
    Base class for all page objects.

    Provides common methods for element interaction, waiting, and navigation
    that are shared across all page objects.
    """

    # Default timeout for explicit waits
    DEFAULT_TIMEOUT = 10

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

    def find_element(
        self, locator: Tuple[str, str], timeout: Optional[int] = None
    ) -> WebElement:
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
        return wait.until(EC.presence_of_element_located(locator))

    def find_elements(
        self, locator: Tuple[str, str], timeout: Optional[int] = None
    ) -> List[WebElement]:
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
            wait.until(EC.presence_of_element_located(locator))
            return self.driver.find_elements(*locator)
        except TimeoutException:
            return []

    def find_element_by_accessibility_id(
        self, accessibility_id: str, timeout: Optional[int] = None
    ) -> WebElement:
        """
        Find element by accessibility identifier.

        Args:
            accessibility_id: The accessibility identifier.
            timeout: Optional timeout override.

        Returns:
            The found WebElement.
        """
        return self.find_element((self.By.ACCESSIBILITY_ID, accessibility_id), timeout)

    def find_element_by_predicate(
        self, predicate: str, timeout: Optional[int] = None
    ) -> WebElement:
        """
        Find element using iOS predicate string.

        Args:
            predicate: iOS predicate string (e.g., "label == 'Settings'").
            timeout: Optional timeout override.

        Returns:
            The found WebElement.
        """
        return self.find_element((self.By.IOS_PREDICATE, predicate), timeout)

    def find_element_by_class_chain(
        self, class_chain: str, timeout: Optional[int] = None
    ) -> WebElement:
        """
        Find element using iOS class chain.

        Args:
            class_chain: iOS class chain string.
            timeout: Optional timeout override.

        Returns:
            The found WebElement.
        """
        return self.find_element((self.By.IOS_CLASS_CHAIN, class_chain), timeout)

    # -------------------------------------------------------------------------
    # Element Interaction Methods
    # -------------------------------------------------------------------------

    def click(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> None:
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
        locator: Tuple[str, str],
        text: str,
        clear_first: bool = True,
        timeout: Optional[int] = None,
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

    def get_text(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> str:
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

    def get_attribute(
        self, locator: Tuple[str, str], attribute: str, timeout: Optional[int] = None
    ) -> Optional[str]:
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
        return element.get_attribute(attribute)

    # -------------------------------------------------------------------------
    # Wait Methods
    # -------------------------------------------------------------------------

    def wait_for_visible(
        self, locator: Tuple[str, str], timeout: Optional[int] = None
    ) -> WebElement:
        """
        Wait for element to be visible.

        Args:
            locator: Tuple of (By strategy, locator value).
            timeout: Optional timeout override.

        Returns:
            The visible WebElement.
        """
        wait = self._get_wait(timeout)
        return wait.until(EC.visibility_of_element_located(locator))

    def wait_for_clickable(
        self, locator: Tuple[str, str], timeout: Optional[int] = None
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
        return wait.until(EC.element_to_be_clickable(locator))

    def wait_for_invisible(
        self, locator: Tuple[str, str], timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for element to become invisible.

        Args:
            locator: Tuple of (By strategy, locator value).
            timeout: Optional timeout override.

        Returns:
            True if element is invisible.
        """
        wait = self._get_wait(timeout)
        return wait.until(EC.invisibility_of_element_located(locator))

    def wait_for_text_present(
        self, locator: Tuple[str, str], text: str, timeout: Optional[int] = None
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
        return wait.until(EC.text_to_be_present_in_element(locator, text))

    # -------------------------------------------------------------------------
    # State Check Methods
    # -------------------------------------------------------------------------

    def is_element_present(self, locator: Tuple[str, str], timeout: int = 2) -> bool:
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

    def is_element_visible(self, locator: Tuple[str, str], timeout: int = 2) -> bool:
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

    def is_element_enabled(self, locator: Tuple[str, str]) -> bool:
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
        self, locator: Tuple[str, str], max_scrolls: int = 5, direction: str = "down"
    ) -> Optional[WebElement]:
        """
        Scroll until element is found.

        Args:
            locator: Tuple of (By strategy, locator value).
            max_scrolls: Maximum scroll attempts.
            direction: Scroll direction ("up" or "down").

        Returns:
            The found element or None if not found.
        """
        for _ in range(max_scrolls):
            if self.is_element_visible(locator, timeout=1):
                return self.find_element(locator)

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
        """Tap the navigation back button."""
        back_button = (self.By.ACCESSIBILITY_ID, "Back")
        if self.is_element_present(back_button):
            self.click(back_button)

    def tap_done_button(self) -> None:
        """Tap a Done button if present."""
        done_button = (self.By.ACCESSIBILITY_ID, "Done")
        if self.is_element_present(done_button):
            self.click(done_button)

    def dismiss_keyboard(self) -> None:
        """Dismiss the keyboard if present."""
        try:
            self.driver.hide_keyboard()
        except Exception:
            # Keyboard might not be present
            pass

    # -------------------------------------------------------------------------
    # Alert Handling
    # -------------------------------------------------------------------------

    def accept_alert(self, timeout: int = 5) -> bool:
        """
        Accept an alert if present.

        Args:
            timeout: Time to wait for alert.

        Returns:
            True if alert was accepted.
        """
        try:
            wait = self._get_wait(timeout)
            wait.until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
            return True
        except TimeoutException:
            return False

    def dismiss_alert(self, timeout: int = 5) -> bool:
        """
        Dismiss an alert if present.

        Args:
            timeout: Time to wait for alert.

        Returns:
            True if alert was dismissed.
        """
        try:
            wait = self._get_wait(timeout)
            wait.until(EC.alert_is_present())
            self.driver.switch_to.alert.dismiss()
            return True
        except TimeoutException:
            return False

    def get_alert_text(self, timeout: int = 5) -> Optional[str]:
        """
        Get alert text if present.

        Args:
            timeout: Time to wait for alert.

        Returns:
            Alert text or None.
        """
        try:
            wait = self._get_wait(timeout)
            wait.until(EC.alert_is_present())
            return self.driver.switch_to.alert.text
        except TimeoutException:
            return None

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

    def _get_wait(self, timeout: Optional[int]) -> WebDriverWait:
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
