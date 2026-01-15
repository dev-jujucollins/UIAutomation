"""Calendar Onboarding Page object for handling first-time launch screens."""

from ..base_page import BasePage


class CalendarOnboardingPage(BasePage):
    """
    Page object for Calendar app onboarding screens.

    Handles the permission dialogs and welcome screens that appear
    when the Calendar app is launched for the first time.

    Onboarding flow on iOS 26.2:
    1. Location Permission Alert - "Allow "Calendar" to use your location?"
    2. Notifications Permission Alert - "Calendar Would Like to Send You Notifications"
    """

    # Location Permission Alert
    # Alert title: "Allow "Calendar" to use your location?"
    LOCATION_ALERT = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeAlert' AND name CONTAINS 'location'",
    )
    LOCATION_ALERT_TITLE = (
        BasePage.By.ACCESSIBILITY_ID,
        'Allow "Calendar" to use your location?',
    )

    # Location permission buttons
    ALLOW_ONCE_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Allow Once")
    ALLOW_WHILE_USING_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Allow While Using App")

    # Notifications Permission Alert
    # Alert title: "Calendar Would Like to Send You Notifications"
    NOTIFICATIONS_ALERT = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeAlert' AND name CONTAINS 'Notifications'",
    )
    NOTIFICATIONS_ALERT_TITLE = (
        BasePage.By.IOS_PREDICATE,
        "label CONTAINS 'Send You Notifications'",
    )

    # Notification permission buttons
    ALLOW_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Allow")

    # Shared deny button (used by both location and notifications alerts)
    # Use predicate with BEGINSWITH 'Don' to handle special apostrophe characters
    DONT_ALLOW_BUTTON = (
        BasePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeButton' AND label BEGINSWITH 'Don'",
    )

    # Generic onboarding buttons (for future screens)
    CONTINUE_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Continue")
    NEXT_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Next")
    GET_STARTED_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Get Started")
    SKIP_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Skip")
    DONE_BUTTON = (BasePage.By.ACCESSIBILITY_ID, "Done")

    # -------------------------------------------------------------------------
    # Location Permission Methods
    # -------------------------------------------------------------------------

    def is_location_permission_showing(self, timeout: int = 3) -> bool:
        """
        Check if the location permission dialog is displayed.

        Args:
            timeout: Time to wait for the alert.

        Returns:
            True if the location permission alert is showing.
        """
        return self.is_element_present(self.LOCATION_ALERT, timeout=timeout)

    def allow_location_once(self) -> bool:
        """
        Allow location access once.

        Returns:
            True if the button was clicked, False if alert wasn't showing.
        """
        if self.is_element_present(self.ALLOW_ONCE_BUTTON, timeout=2):
            self.click(self.ALLOW_ONCE_BUTTON)
            return True
        return False

    def allow_location_while_using(self) -> bool:
        """
        Allow location access while using the app.

        Returns:
            True if the button was clicked, False if alert wasn't showing.
        """
        if self.is_element_present(self.ALLOW_WHILE_USING_BUTTON, timeout=2):
            self.click(self.ALLOW_WHILE_USING_BUTTON)
            return True
        return False

    def dismiss_location_permission(self) -> bool:
        """
        Dismiss location permission by tapping 'Allow Once'.

        Note: We use 'Allow Once' instead of 'Don't Allow' because the
        apostrophe character in iOS is a special unicode character that's
        difficult to match reliably.

        Returns:
            True if the button was clicked, False if alert wasn't showing.
        """
        if self.is_location_permission_showing(timeout=1):
            if self.is_element_present(self.ALLOW_ONCE_BUTTON, timeout=2):
                self.click(self.ALLOW_ONCE_BUTTON)
                return True
        return False

    # -------------------------------------------------------------------------
    # Notifications Permission Methods
    # -------------------------------------------------------------------------

    def is_notifications_permission_showing(self, timeout: int = 3) -> bool:
        """
        Check if the notifications permission dialog is displayed.

        Args:
            timeout: Time to wait for the alert.

        Returns:
            True if the notifications permission alert is showing.
        """
        return self.is_element_present(self.NOTIFICATIONS_ALERT, timeout=timeout)

    def allow_notifications(self) -> bool:
        """
        Allow notifications.

        Returns:
            True if the button was clicked, False if alert wasn't showing.
        """
        if self.is_element_present(self.ALLOW_BUTTON, timeout=2):
            self.click(self.ALLOW_BUTTON)
            return True
        return False

    def dismiss_notifications_permission(self) -> bool:
        """
        Dismiss notifications permission by tapping 'Allow'.

        Note: We use 'Allow' instead of 'Don't Allow' because the
        apostrophe character in iOS is a special unicode character that's
        difficult to match reliably.

        Returns:
            True if the button was clicked, False if alert wasn't showing.
        """
        if self.is_notifications_permission_showing(timeout=1):
            if self.is_element_present(self.ALLOW_BUTTON, timeout=2):
                self.click(self.ALLOW_BUTTON)
                return True
        return False

    def dismiss_all_onboarding(self, max_screens: int = 5) -> bool:
        """
        Dismiss all onboarding screens to reach the main Calendar view.

        This method handles all known onboarding screens including:
        - Location permission dialog (taps 'Allow Once')
        - Notifications permission dialog (taps 'Allow')
        - Any future welcome/intro screens

        Args:
            max_screens: Maximum number of screens to attempt dismissing.

        Returns:
            True if all onboarding was dismissed successfully.
        """
        import time

        for _ in range(max_screens):
            handled_screen = False

            # Handle location permission
            if self.is_location_permission_showing(timeout=2):
                handled_screen = self.dismiss_location_permission()
                if handled_screen:
                    time.sleep(0.5)
                    continue

            # Handle notifications permission
            if self.is_notifications_permission_showing(timeout=2):
                handled_screen = self.dismiss_notifications_permission()
                if handled_screen:
                    time.sleep(0.5)
                    continue

            # Handle generic continue/next/skip buttons
            generic_buttons = [
                self.CONTINUE_BUTTON,
                self.NEXT_BUTTON,
                self.GET_STARTED_BUTTON,
                self.SKIP_BUTTON,
                self.DONE_BUTTON,
            ]

            for button in generic_buttons:
                if self.is_element_present(button, timeout=1):
                    self.click(button)
                    time.sleep(0.5)
                    handled_screen = True
                    break

            if not handled_screen:
                # No more onboarding screens found
                return True

        return True

    def get_location_alert_text(self) -> str | None:
        """
        Get the text from the location permission alert.

        Returns:
            The alert text or None if not present.
        """
        if self.is_location_permission_showing():
            try:
                element = self.find_element(self.LOCATION_ALERT_TITLE, timeout=2)
                return element.get_attribute("label")
            except Exception:
                return None
        return None
