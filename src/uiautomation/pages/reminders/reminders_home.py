"""Reminders lists overview, observed on the English iOS 27.2 simulator."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException

from uiautomation.utils.locators import predicate_literal

from ..base_page import BasePage
from ..system_prompts import answer_system_prompt

if TYPE_CHECKING:
    from .new_reminder import NewReminderPage
    from .reminder_list import ReminderListPage


class RemindersHomePage(BasePage):
    """The overview of smart lists (Today, Scheduled, All, Completed) and My Lists.

    The overview also shows a "Sync Reminders with iCloud" banner whose "Go to Settings"
    opens Settings' Apple Account sign-in; nothing here taps it.
    """

    LISTS_NAV = (BasePage.By.ACCESSIBILITY_ID, "Reminders.TTRIAccountsListsView")
    NEW_REMINDER = (BasePage.By.ACCESSIBILITY_ID, "New Reminder")
    ADD_LIST = (BasePage.By.ACCESSIBILITY_ID, "Add List")
    LISTS_TABLE = (BasePage.By.ACCESSIBILITY_ID, "AccountsList.ID.AccountsListTable")
    COMPLETED = (BasePage.By.ACCESSIBILITY_ID, "Completed")
    BACK_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "BackButton")
    # First-launch "Welcome to Reminders" screen.
    WELCOME_TITLE = (BasePage.By.ACCESSIBILITY_ID, "Welcome to Reminders")
    WELCOME_CONTINUE = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND name == 'Continue'",
    )
    DEFAULT_LIST = "Reminders"
    LAUNCH_TIMEOUT = 30

    HEALTH_LOCATORS = ("LISTS_NAV", "NEW_REMINDER", "ADD_LIST", "COMPLETED")

    def _visible(self, locator: tuple[str, str]) -> WebElement | None:
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return element
            except StaleElementReferenceException:
                continue
        return None

    def wait_until_ready(self) -> None:
        """Get past first-launch screens and any restored list to the overview.

        Reminders reopens the screen it was last on, so a list view is left with Back.
        """

        def ready(_: WebDriver) -> bool:
            try:
                if answer_system_prompt(self.driver, "Reminders"):
                    return False
                if self._visible(self.WELCOME_TITLE):
                    button = self._visible(self.WELCOME_CONTINUE)
                    if button:
                        button.click()
                    return False
                if self._visible(self.LISTS_NAV):
                    return bool(self._visible(self.NEW_REMINDER) and self._visible(self.ADD_LIST))
                back = self._visible(self.BACK_BUTTON)
                if back:
                    back.click()
                return False
            except StaleElementReferenceException:
                return False

        self._get_wait(self.LAUNCH_TIMEOUT).until(ready, "Reminders lists overview not ready")

    @classmethod
    def list_cell(cls, name: str) -> tuple[str, str]:
        """A list under My Lists; its label is "<name>, <n> reminder(s)"."""
        return (
            cls.By.IOS_PREDICATE,
            f"type == 'XCUIElementTypeCell' AND label BEGINSWITH {predicate_literal(name + ', ')}",
        )

    def _scroll_to_list(self, name: str, max_swipes: int = 5) -> WebElement:
        """My Lists sits below the smart lists; at large text sizes it starts off screen.

        Off-screen cells are not in the accessibility tree, and a whole-app scroll does not
        move this list, so swipe the list itself until the cell appears.
        """
        for attempt in range(max_swipes + 1):
            # Presence, not is_displayed: cells off screen are absent from the tree, and a
            # cell can briefly report hidden while a sheet closes over it.
            cells = self.driver.find_elements(*self.list_cell(name))
            if cells:
                return cells[0]
            if attempt == max_swipes:
                break
            table = self.find_element(self.LISTS_TABLE)
            self.driver.execute_script("mobile: swipe", {"elementId": table.id, "direction": "up"})
        raise AssertionError(f"Reminders list {name!r} not found after {max_swipes} swipes")

    def list_count(self, name: str = DEFAULT_LIST) -> int:
        """Number of incomplete reminders the overview reports for a list."""
        cell = self._scroll_to_list(name)
        label = cell.get_attribute("label") or ""
        match = re.fullmatch(rf"{re.escape(name)}, (\d+) reminders?", str(label))
        if match is None:
            raise AssertionError(f"Unexpected list label: {label!r}")
        return int(match.group(1))

    def open_new_reminder(self) -> NewReminderPage:
        """Open the New Reminder sheet; from a list, the same button adds an inline row."""
        from .new_reminder import NewReminderPage

        self.click(self.NEW_REMINDER)
        page = NewReminderPage(self.driver)
        page.wait_until_ready()
        return page

    def open_list(self, name: str = DEFAULT_LIST) -> ReminderListPage:
        """Open a list under My Lists."""
        from .reminder_list import ReminderListPage

        self._scroll_to_list(name).click()
        page = ReminderListPage(self.driver, name)
        page.wait_until_ready()
        return page

    def open_completed(self) -> ReminderListPage:
        """Open the Completed smart list, where finished reminders move."""
        from .reminder_list import ReminderListPage

        self.click(self.COMPLETED)
        page = ReminderListPage(self.driver, "Completed")
        page.wait_until_ready()
        return page
