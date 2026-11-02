"""One Reminders list (or the Completed smart list) and its reminder rows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException

from uiautomation.utils.locators import predicate_literal

from ..base_page import BasePage

if TYPE_CHECKING:
    from .reminders_home import RemindersHomePage

ReminderState = Literal["Incomplete", "Completed"]


class ReminderListPage(BasePage):
    """Rows are cells labelled "<title>, Incomplete" or "<title>, Completed[, in <list>]"."""

    BACK_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "BackButton")
    CHECKBOX = (BasePage.By.ACCESSIBILITY_ID, "Circle")
    DELETE_ACTION = (BasePage.By.ACCESSIBILITY_ID, "Delete")

    def __init__(self, driver: WebDriver, name: str) -> None:
        super().__init__(driver)
        self.name = name
        self.NAVIGATION_BAR = (
            self.By.IOS_PREDICATE,
            f"type == 'XCUIElementTypeNavigationBar' AND name == {predicate_literal(name)}",
        )

    def wait_until_ready(self) -> None:
        self.wait_for_visible(self.NAVIGATION_BAR)
        self.wait_for_visible(self.BACK_BUTTON)

    @classmethod
    def row(cls, title: str) -> tuple[str, str]:
        return (
            cls.By.IOS_PREDICATE,
            f"type == 'XCUIElementTypeCell' AND label BEGINSWITH {predicate_literal(title + ', ')}",
        )

    def _row(self, title: str) -> WebElement | None:
        rows = self.driver.find_elements(*self.row(title))
        return rows[0] if rows else None

    def state(self, title: str) -> ReminderState | None:
        """The row's state, or None when the reminder is not in this list."""
        row = self._row(title)
        if row is None:
            return None
        state = str(row.get_attribute("label") or "").removeprefix(f"{title}, ").split(", ")[0]
        if state not in ("Incomplete", "Completed"):
            raise AssertionError(f"Unexpected reminder row label for {title!r}: {state!r}")
        return state

    def wait_for_state(self, title: str, expected: ReminderState | None) -> None:
        def matches(_: WebDriver) -> bool:
            try:
                return self.state(title) == expected
            except StaleElementReferenceException:
                return False

        self._get_wait(None).until(matches, f"{title!r} never became {expected}")

    def complete(self, title: str) -> None:
        """Tick the reminder once; Reminders moves it to Completed a few seconds later."""
        row = self._row(title)
        if row is None:
            raise AssertionError(f"No reminder {title!r} in {self.name}")
        if self.state(title) != "Incomplete":
            raise AssertionError(f"{title!r} is not incomplete")
        row.find_element(*self.CHECKBOX).click()
        self.wait_for_state(title, "Completed")

    def delete(self, title: str) -> None:
        """Swipe the row left and tap Delete; Reminders deletes without confirming."""
        row = self._row(title)
        if row is None:
            raise AssertionError(f"No reminder {title!r} in {self.name}")
        self.driver.execute_script("mobile: swipe", {"elementId": row.id, "direction": "left"})
        self.wait_for_clickable(self.DELETE_ACTION).click()
        self.wait_for_state(title, None)

    def go_back(self) -> RemindersHomePage:
        from .reminders_home import RemindersHomePage

        self.click(self.BACK_BUTTON)
        home = RemindersHomePage(self.driver)
        home.wait_until_ready()
        return home
