"""Calendar Onboarding Page object for handling first-time launch screens."""

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver

from ..base_page import BasePage
from ..system_prompts import answer_system_prompt


class CalendarOnboardingPage(BasePage):
    """
    Page object for Calendar app onboarding prompts.

    Calendar asks for location, notification, and contacts access on first launch, and
    iOS 27 adds a "What’s New in Calendar" sheet. Permission prompts are declined through
    the shared ``system_prompts`` table and the sheet is continued past. Any other alert
    fails the run so new UI is inspected, not tapped through.
    """

    # Full-screen "What’s New in Calendar" sheet shown on first launch in iOS 27.
    # ENDSWITH avoids matching the curly apostrophe in "What’s".
    WHATS_NEW_TITLE = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeStaticText' AND name ENDSWITH 'New in Calendar'",
    )
    WHATS_NEW_CONTINUE = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND name == 'Continue'",
    )

    def dismiss_known_prompt(self) -> bool:
        """Decline one known system prompt or close the What's New sheet.

        Returns:
            True if a prompt was dismissed, False if none is showing.

        Raises:
            AssertionError: If a visible alert is not a known system prompt.
        """
        if answer_system_prompt(self.driver, "Calendar"):
            return True
        if self.is_element_visible(self.WHATS_NEW_TITLE, timeout=0):
            self.click(self.WHATS_NEW_CONTINUE)
            return True
        return False

    def dismiss_all_onboarding(self, timeout: int | None = None) -> bool:
        """
        Dismiss known first-launch prompts until Calendar home is visible.

        Args:
            timeout: Optional timeout override.

        Returns:
            True once Calendar home is visible, False if it never appears.

        Raises:
            AssertionError: If an unrecognized alert appears.
        """
        from .calendar_home import CalendarHomePage

        home = CalendarHomePage(self.driver)

        def ready(_: WebDriver) -> bool:
            if self.dismiss_known_prompt():
                return False
            return home.is_element_visible(home.TOOLBAR, timeout=0) or home.is_element_visible(
                home.DAY_VIEW_NAV_BAR, timeout=0
            )

        try:
            self._get_wait(timeout).until(ready)
        except TimeoutException:
            return False
        return True
