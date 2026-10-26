"""Calendar Onboarding Page object for handling first-time launch screens."""

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver

from ..base_page import BasePage


class CalendarOnboardingPage(BasePage):
    """
    Page object for Calendar app onboarding prompts.

    Calendar asks for location and notification access on first launch, and iOS 27
    adds a "What’s New in Calendar" sheet. The permissions are declined and the sheet
    is continued past. Any other alert fails the run so new UI is inspected, not
    tapped through.
    """

    LOCATION_ALERT = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeAlert' AND name CONTAINS 'location'",
    )
    NOTIFICATIONS_ALERT = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeAlert' AND name CONTAINS 'Notifications'",
    )

    # Shared deny button (used by both location and notifications alerts)
    # Use predicate with BEGINSWITH 'Don' to handle special apostrophe characters
    DONT_ALLOW_BUTTON = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND label BEGINSWITH 'Don'",
    )

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

    def is_location_permission_showing(self, timeout: int = 3) -> bool:
        """
        Check if the location permission dialog is displayed.

        Args:
            timeout: Time to wait for the alert.

        Returns:
            True if the location permission alert is showing.
        """
        return self.is_element_present(self.LOCATION_ALERT, timeout=timeout)

    def dismiss_location_permission(self) -> bool:
        """
        Dismiss location permission by declining access.

        Returns:
            True if the button was clicked, False if alert wasn't showing.
        """
        if self.is_location_permission_showing(timeout=1):
            if self.is_element_present(self.DONT_ALLOW_BUTTON, timeout=2):
                self.click(self.DONT_ALLOW_BUTTON)
                return True
        return False

    def is_notifications_permission_showing(self, timeout: int = 3) -> bool:
        """
        Check if the notifications permission dialog is displayed.

        Args:
            timeout: Time to wait for the alert.

        Returns:
            True if the notifications permission alert is showing.
        """
        return self.is_element_present(self.NOTIFICATIONS_ALERT, timeout=timeout)

    def dismiss_notifications_permission(self) -> bool:
        """
        Dismiss notifications permission by declining access.

        Returns:
            True if the button was clicked, False if alert wasn't showing.
        """
        if self.is_notifications_permission_showing(timeout=1):
            if self.is_element_present(self.DONT_ALLOW_BUTTON, timeout=2):
                self.click(self.DONT_ALLOW_BUTTON)
                return True
        return False

    def dismiss_known_prompt(self) -> bool:
        """Decline one recognized Calendar alert or close the What's New sheet.

        Returns:
            True if a prompt was dismissed, False if none is showing.

        Raises:
            AssertionError: If a visible alert is not a known Calendar prompt.
        """
        for alert in self.driver.find_elements(self.By.CLASS_NAME, "XCUIElementTypeAlert"):
            try:
                if not alert.is_displayed():
                    continue
                title = alert.get_attribute("name") or ""
            except StaleElementReferenceException:
                # The alert is animating away; check again on the next poll.
                return False
            # Match on words, not exact titles, so curly or straight quotes both work.
            if "Calendar" in title and ("location" in title or "Notifications" in title):
                alert.find_element(*self.DONT_ALLOW_BUTTON).click()
                return True
            raise AssertionError(f"Unexpected Calendar alert: {title}")
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
