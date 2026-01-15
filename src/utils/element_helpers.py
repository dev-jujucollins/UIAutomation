"""
Element helper utilities for iOS automation.
"""

from typing import Any, Dict, List, Optional, Tuple

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement


class ElementHelpers:
    """
    Utility class providing helper methods for element interactions.

    Contains methods for common element operations that don't fit
    neatly into page objects.
    """

    def __init__(self, driver: WebDriver):
        """
        Initialize element helpers.

        Args:
            driver: Appium WebDriver instance.
        """
        self.driver = driver

    # -------------------------------------------------------------------------
    # Element Information
    # -------------------------------------------------------------------------

    def get_element_attributes(self, element: WebElement) -> Dict[str, Any]:
        """
        Get all common attributes of an element.

        Args:
            element: WebElement to inspect.

        Returns:
            Dictionary of attribute names and values.
        """
        attributes = {}
        attr_names = [
            "name",
            "label",
            "value",
            "type",
            "enabled",
            "visible",
            "accessible",
            "rect",
        ]

        for attr in attr_names:
            try:
                attributes[attr] = element.get_attribute(attr)
            except Exception:
                attributes[attr] = None

        return attributes

    def get_element_center(self, element: WebElement) -> Tuple[int, int]:
        """
        Get the center coordinates of an element.

        Args:
            element: WebElement to get center of.

        Returns:
            Tuple of (x, y) coordinates.
        """
        rect = element.rect
        x = rect["x"] + rect["width"] / 2
        y = rect["y"] + rect["height"] / 2
        return (int(x), int(y))

    def get_element_bounds(self, element: WebElement) -> Dict[str, int]:
        """
        Get the bounding rectangle of an element.

        Args:
            element: WebElement to get bounds of.

        Returns:
            Dictionary with x, y, width, height.
        """
        return element.rect

    # -------------------------------------------------------------------------
    # Element State Checks
    # -------------------------------------------------------------------------

    def is_switch_on(self, element: WebElement) -> bool:
        """
        Check if a switch element is in the ON state.

        Args:
            element: Switch WebElement.

        Returns:
            True if switch is ON.
        """
        value = element.get_attribute("value")
        return value == "1"

    def is_checkbox_checked(self, element: WebElement) -> bool:
        """
        Check if a checkbox element is checked.

        Args:
            element: Checkbox WebElement.

        Returns:
            True if checkbox is checked.
        """
        value = element.get_attribute("value")
        return value == "1" or value == "true"

    def is_element_selected(self, element: WebElement) -> bool:
        """
        Check if an element is selected.

        Args:
            element: WebElement to check.

        Returns:
            True if element is selected.
        """
        return element.is_selected()

    # -------------------------------------------------------------------------
    # Finding Elements with Predicates
    # -------------------------------------------------------------------------

    def find_by_label(self, label: str) -> Optional[WebElement]:
        """
        Find element by its label attribute.

        Args:
            label: Label text to search for.

        Returns:
            Found element or None.
        """
        predicate = f"label == '{label}'"
        try:
            return self.driver.find_element(AppiumBy.IOS_PREDICATE, predicate)
        except Exception:
            return None

    def find_by_label_contains(self, text: str) -> Optional[WebElement]:
        """
        Find element whose label contains specified text.

        Args:
            text: Text to search for in label.

        Returns:
            Found element or None.
        """
        predicate = f"label CONTAINS '{text}'"
        try:
            return self.driver.find_element(AppiumBy.IOS_PREDICATE, predicate)
        except Exception:
            return None

    def find_all_by_type(self, element_type: str) -> List[WebElement]:
        """
        Find all elements of a specific type.

        Args:
            element_type: XCUIElement type (e.g., "XCUIElementTypeButton").

        Returns:
            List of matching elements.
        """
        predicate = f"type == '{element_type}'"
        return self.driver.find_elements(AppiumBy.IOS_PREDICATE, predicate)

    def find_buttons(self) -> List[WebElement]:
        """
        Find all button elements.

        Returns:
            List of button elements.
        """
        return self.find_all_by_type("XCUIElementTypeButton")

    def find_text_fields(self) -> List[WebElement]:
        """
        Find all text field elements.

        Returns:
            List of text field elements.
        """
        return self.find_all_by_type("XCUIElementTypeTextField")

    def find_switches(self) -> List[WebElement]:
        """
        Find all switch elements.

        Returns:
            List of switch elements.
        """
        return self.find_all_by_type("XCUIElementTypeSwitch")

    def find_cells(self) -> List[WebElement]:
        """
        Find all table cell elements.

        Returns:
            List of cell elements.
        """
        return self.find_all_by_type("XCUIElementTypeCell")

    # -------------------------------------------------------------------------
    # Gesture Helpers
    # -------------------------------------------------------------------------

    def tap_at_coordinates(self, x: int, y: int) -> None:
        """
        Tap at specific screen coordinates.

        Args:
            x: X coordinate.
            y: Y coordinate.
        """
        self.driver.execute_script("mobile: tap", {"x": x, "y": y})

    def tap_element_center(self, element: WebElement) -> None:
        """
        Tap at the center of an element.

        Args:
            element: Element to tap.
        """
        x, y = self.get_element_center(element)
        self.tap_at_coordinates(x, y)

    def long_press(self, element: WebElement, duration: float = 1.0) -> None:
        """
        Perform a long press on an element.

        Args:
            element: Element to long press.
            duration: Press duration in seconds.
        """
        x, y = self.get_element_center(element)
        self.driver.execute_script(
            "mobile: touchAndHold", {"x": x, "y": y, "duration": duration}
        )

    def double_tap(self, element: WebElement) -> None:
        """
        Perform a double tap on an element.

        Args:
            element: Element to double tap.
        """
        x, y = self.get_element_center(element)
        self.driver.execute_script("mobile: doubleTap", {"x": x, "y": y})

    def drag_and_drop(
        self, source: WebElement, target: WebElement, duration: float = 0.5
    ) -> None:
        """
        Drag from one element to another.

        Args:
            source: Element to drag from.
            target: Element to drag to.
            duration: Drag duration in seconds.
        """
        source_x, source_y = self.get_element_center(source)
        target_x, target_y = self.get_element_center(target)

        self.driver.execute_script(
            "mobile: dragFromToForDuration",
            {
                "fromX": source_x,
                "fromY": source_y,
                "toX": target_x,
                "toY": target_y,
                "duration": duration,
            },
        )

    # -------------------------------------------------------------------------
    # Text Helpers
    # -------------------------------------------------------------------------

    def clear_and_type(self, element: WebElement, text: str) -> None:
        """
        Clear an element and type new text.

        Args:
            element: Text input element.
            text: Text to type.
        """
        element.clear()
        element.send_keys(text)

    def get_all_text_on_screen(self) -> List[str]:
        """
        Get all visible text on the current screen.

        Returns:
            List of text strings.
        """
        static_texts = self.find_all_by_type("XCUIElementTypeStaticText")
        texts = []
        for element in static_texts:
            try:
                text = element.text
                if text:
                    texts.append(text)
            except Exception:
                continue
        return texts

    # -------------------------------------------------------------------------
    # Debug Helpers
    # -------------------------------------------------------------------------

    def print_element_tree(
        self, element: Optional[WebElement] = None, indent: int = 0
    ) -> str:
        """
        Get a formatted string representation of the element hierarchy.

        Args:
            element: Starting element (None for entire page).
            indent: Current indentation level.

        Returns:
            Formatted element tree string.
        """
        # This returns the page source which shows the element hierarchy
        return self.driver.page_source

    def highlight_element(self, element: WebElement) -> None:
        """
        Highlight an element by drawing a border (for debugging).

        Note: This uses JavaScript execution which may not work on all elements.

        Args:
            element: Element to highlight.
        """
        # iOS doesn't support direct JavaScript injection like web
        # Instead, we can take a screenshot with element bounds logged
        rect = element.rect
        print(
            f"Element bounds: x={rect['x']}, y={rect['y']}, "
            f"width={rect['width']}, height={rect['height']}"
        )
