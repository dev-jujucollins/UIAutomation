"""
Wait helper utilities for iOS automation.
"""

import time
from typing import Callable, Optional, TypeVar

from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait

T = TypeVar("T")


class WaitHelpers:
    """
    Utility class for various wait operations.

    Provides flexible waiting methods beyond standard explicit waits.
    """

    def __init__(self, driver: WebDriver, default_timeout: int = 10):
        """
        Initialize wait helpers.

        Args:
            driver: Appium WebDriver instance.
            default_timeout: Default timeout in seconds.
        """
        self.driver = driver
        self.default_timeout = default_timeout

    def wait_for_condition(
        self,
        condition: Callable[[], T],
        timeout: Optional[int] = None,
        poll_frequency: float = 0.5,
        message: str = "Condition not met within timeout",
    ) -> T:
        """
        Wait for a custom condition to be true.

        Args:
            condition: Callable that returns truthy value when condition is met.
            timeout: Maximum wait time in seconds.
            poll_frequency: How often to check condition in seconds.
            message: Error message if timeout occurs.

        Returns:
            The truthy value returned by the condition.

        Raises:
            TimeoutException: If condition not met within timeout.
        """
        timeout = timeout or self.default_timeout
        end_time = time.time() + timeout

        while time.time() < end_time:
            try:
                result = condition()
                if result:
                    return result
            except Exception:
                pass
            time.sleep(poll_frequency)

        raise TimeoutException(message)

    def wait_for_app_ready(self, bundle_id: str, timeout: Optional[int] = None) -> bool:
        """
        Wait for an app to be in foreground and ready.

        Args:
            bundle_id: The app's bundle identifier.
            timeout: Maximum wait time.

        Returns:
            True if app is ready.
        """

        def check_app_foreground():
            state = self.driver.query_app_state(bundle_id)
            return state == 4  # 4 = foreground

        try:
            return self.wait_for_condition(
                check_app_foreground,
                timeout=timeout,
                message=f"App {bundle_id} not ready",
            )
        except TimeoutException:
            return False

    def wait_for_element_count(
        self, locator: tuple, count: int, timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for a specific number of elements to be present.

        Args:
            locator: Element locator tuple.
            count: Expected number of elements.
            timeout: Maximum wait time.

        Returns:
            True if expected count reached.
        """

        def check_count():
            elements = self.driver.find_elements(*locator)
            return len(elements) == count

        try:
            return self.wait_for_condition(
                check_count,
                timeout=timeout,
                message=f"Expected {count} elements, condition not met",
            )
        except TimeoutException:
            return False

    def wait_for_element_attribute(
        self,
        locator: tuple,
        attribute: str,
        expected_value: str,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        Wait for element attribute to have expected value.

        Args:
            locator: Element locator tuple.
            attribute: Attribute name.
            expected_value: Expected attribute value.
            timeout: Maximum wait time.

        Returns:
            True if attribute has expected value.
        """

        def check_attribute():
            try:
                element = self.driver.find_element(*locator)
                actual_value = element.get_attribute(attribute)
                return actual_value == expected_value
            except Exception:
                return False

        try:
            return self.wait_for_condition(
                check_attribute,
                timeout=timeout,
                message=f"Attribute {attribute} never became {expected_value}",
            )
        except TimeoutException:
            return False

    def wait_for_text_change(
        self, locator: tuple, initial_text: str, timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for element text to change from initial value.

        Args:
            locator: Element locator tuple.
            initial_text: Text value to change from.
            timeout: Maximum wait time.

        Returns:
            True if text changed.
        """

        def check_text_changed():
            try:
                element = self.driver.find_element(*locator)
                return element.text != initial_text
            except Exception:
                return False

        try:
            return self.wait_for_condition(
                check_text_changed,
                timeout=timeout,
                message=f"Text never changed from '{initial_text}'",
            )
        except TimeoutException:
            return False

    def wait_for_animation_complete(self, timeout: float = 2.0) -> None:
        """
        Wait for animations to complete.

        This is a simple sleep-based wait for UI animations.
        For more precise control, consider using accessibility identifiers
        that appear after animations complete.

        Args:
            timeout: Time to wait for animation.
        """
        time.sleep(timeout)

    def wait_for_network_idle(
        self, timeout: Optional[int] = None, idle_time: float = 1.0
    ) -> bool:
        """
        Wait for network activity to become idle.

        Note: This is a simplified implementation. For real network
        monitoring, consider using proxy tools or network profiling.

        Args:
            timeout: Maximum wait time.
            idle_time: Time network must be idle.

        Returns:
            True (always, as this is simplified).
        """
        # Simplified implementation - just wait
        time.sleep(idle_time)
        return True

    def retry_on_failure(
        self,
        action: Callable[[], T],
        max_retries: int = 3,
        retry_delay: float = 1.0,
        exceptions: tuple = (Exception,),
    ) -> T:
        """
        Retry an action on failure.

        Args:
            action: Callable to execute.
            max_retries: Maximum number of retry attempts.
            retry_delay: Delay between retries in seconds.
            exceptions: Tuple of exceptions to catch and retry on.

        Returns:
            Result of the action.

        Raises:
            The last exception if all retries fail.
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return action()
            except exceptions as e:
                last_exception = e
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        raise last_exception

    def wait_until_stable(
        self,
        value_getter: Callable[[], T],
        stability_time: float = 1.0,
        timeout: Optional[int] = None,
        poll_frequency: float = 0.2,
    ) -> T:
        """
        Wait until a value remains stable for a period of time.

        Useful for waiting for loading indicators, counters, etc.

        Args:
            value_getter: Callable that returns the value to monitor.
            stability_time: Time value must remain stable.
            timeout: Maximum wait time.
            poll_frequency: How often to check value.

        Returns:
            The stable value.

        Raises:
            TimeoutException: If value never stabilizes.
        """
        timeout = timeout or self.default_timeout
        end_time = time.time() + timeout

        last_value = None
        stable_since = None

        while time.time() < end_time:
            try:
                current_value = value_getter()

                if current_value == last_value:
                    if stable_since is None:
                        stable_since = time.time()
                    elif time.time() - stable_since >= stability_time:
                        return current_value
                else:
                    last_value = current_value
                    stable_since = None
            except Exception:
                last_value = None
                stable_since = None

            time.sleep(poll_frequency)

        raise TimeoutException("Value never stabilized within timeout")
