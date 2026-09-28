"""Owned all-day event lifecycle on the observed English iOS 27 Calendar UI."""

from collections.abc import Collection

from appium.webdriver.webdriver import WebDriver
from appium.webdriver.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException

from uiautomation.drivers.ios_driver import SystemApps
from uiautomation.utils.app_launcher import AppLauncher

from .calendar_home import CalendarHomePage
from .calendar_onboarding import CalendarOnboardingPage
from .new_event import NewEventPage


class CalendarEventsPage(CalendarHomePage):
    """Create and remove only event titles assigned to this test run."""

    DETAILS_TITLE = (CalendarHomePage.By.ACCESSIBILITY_ID, "event-details-title-text")
    EDIT_BUTTON = (CalendarHomePage.By.ACCESSIBILITY_ID, "event-details-edit-button")
    DELETE_BUTTON = (CalendarHomePage.By.ACCESSIBILITY_ID, "delete-event-cell")
    DETAIL_CLOSE = (CalendarHomePage.By.ACCESSIBILITY_ID, "cancel-button")
    DELETE_SHEET = (
        CalendarHomePage.By.IOS_PREDICATE,
        "type == 'XCUIElementTypeSheet' AND name == 'Are you sure you want to delete this event?'",
    )
    DELETE_CONFIRM = (CalendarHomePage.By.ACCESSIBILITY_ID, "delete-alert-button")

    def __init__(self, driver: WebDriver, owned_titles: Collection[str]) -> None:
        """Remember the exact generated titles this lifecycle is allowed to change.

        Args:
            driver: Active Appium session.
            owned_titles: All original and edited titles, registered before creation.
        """
        super().__init__(driver)
        if not owned_titles or any(not title.strip() for title in owned_titles):
            raise ValueError("Calendar lifecycle requires non-empty owned titles")
        self.owned_titles = frozenset(owned_titles)
        self._pending_delete: str | None = None

    def _require_owned(self, title: str) -> None:
        if title not in self.owned_titles:
            raise ValueError(f"Calendar title is not owned by this run: {title!r}")

    def _event_locator(self, title: str) -> tuple[str, str]:
        self._require_owned(title)
        return self.By.ACCESSIBILITY_ID, f"event-shown:{title}"

    def _visible(self, locator: tuple[str, str]) -> WebElement | None:
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return element
            except StaleElementReferenceException:
                continue
        return None

    def _dismiss_notifications(self) -> bool:
        if self._visible(CalendarOnboardingPage.NOTIFICATIONS_ALERT):
            return CalendarOnboardingPage(self.driver).dismiss_notifications_permission()
        return False

    def _home_ready(self) -> bool:
        return bool(
            self._visible(self.DAY_VIEW_NAV_BAR)
            and self._visible(self.TODAY_BUTTON)
            and self._visible(self.ADD_BUTTON)
            and not self._visible(NewEventPage.TITLE_FIELD)
            and not self._visible(self.DETAILS_TITLE)
            and not self._visible((self.By.CLASS_NAME, "XCUIElementTypeAlert"))
            and not self._visible((self.By.CLASS_NAME, "XCUIElementTypeSheet"))
        )

    def wait_for_home(self) -> None:
        """Wait through the observed notification prompt for an unobstructed day view."""

        def ready(_: WebDriver) -> bool:
            if self._dismiss_notifications():
                return False
            return self._home_ready()

        self._get_wait(None).until(ready, "Calendar day view did not become ready")

    def close_to_home(self) -> None:
        """Close owned editor/detail states; finish only a deletion already verified here."""
        self._dismiss_notifications()
        if self._visible(self.DELETE_SHEET):
            if self._pending_delete not in self.owned_titles:
                raise AssertionError("Cannot confirm an unowned Calendar deletion")
            self._confirm_delete()
        if self.driver.find_elements(*NewEventPage.TITLE_FIELD) or self._visible(
            self.DETAILS_TITLE
        ):
            NewEventPage(self.driver).discard()
        self.wait_for_home()

    def create_all_day(self, title: str) -> None:
        """Create a unique all-day event today and require its visible day-view entry.

        Args:
            title: Exact title registered for this run before creation.
        """
        self._require_owned(title)
        self.close_to_home()
        self.tap_today()
        if self._visible(self._event_locator(title)):
            raise AssertionError(f"Owned event already exists: {title!r}")
        editor = self.tap_add_event()
        editor.set_title(title)
        editor.enable_all_day()
        editor.wait_for_attribute(editor.ALL_DAY_SWITCH, "value", "1")
        editor.tap_done()
        self.wait_for_home()
        self.wait_for_visible(self._event_locator(title))

    def relaunch(self) -> None:
        """Restart Calendar so subsequent assertions verify persisted data."""
        self.close_to_home()
        launcher = AppLauncher(self.driver)
        launcher.terminate(SystemApps.CALENDAR)
        launcher.launch(SystemApps.CALENDAR)
        self.close_to_home()
        self.tap_today()

    def open_event(self, title: str) -> None:
        """Open the exact owned entry and verify the event detail's title.

        Args:
            title: Exact owned title expected on both the day entry and detail.
        """
        self._require_owned(title)
        self.close_to_home()
        self.click(self._event_locator(title))
        self.wait_for_attribute(self.DETAILS_TITLE, "label", title)

    def rename_event(self, title: str, new_title: str) -> None:
        """Rename an owned event and require its persisted replacement entry.

        Args:
            title: Current owned title.
            new_title: Replacement title registered before editing.
        """
        self._require_owned(new_title)
        self.open_event(title)
        self.click(self.EDIT_BUTTON)
        editor = NewEventPage(self.driver)
        editor.set_title(new_title)
        editor.tap_done()
        self.close_to_home()
        self.wait_for_visible(self._event_locator(new_title))
        self.assert_absent(title)

    def _confirm_delete(self) -> None:
        self._require_owned(self._pending_delete or "")
        sheet = self.wait_for_visible(self.DELETE_SHEET)
        # iOS 27 reports this observed button as invisible inside its visible
        # confirmation sheet. Scope by the sheet and its exact accessibility ID.
        sheet.find_element(*self.DELETE_CONFIRM).click()
        self.wait_for_invisible(self.DELETE_SHEET)
        self._pending_delete = None

    def delete_event(self, title: str) -> None:
        """Delete only after opening and verifying the exact owned event.

        Args:
            title: Owned event title to remove.
        """
        self.open_event(title)
        self._pending_delete = title
        self.click(self.DELETE_BUTTON)
        self._confirm_delete()
        self.wait_for_home()
        self.assert_absent(title)

    def assert_absent(self, title: str) -> None:
        """Require a usable day view with no visible entry for the exact owned title."""
        self.wait_for_home()
        self.wait_for_invisible(self._event_locator(title))

    def cleanup(self) -> None:
        """Recover known sheets and remove every registered title, including failed renames."""
        self.close_to_home()
        self.tap_today()
        failures: list[str] = []
        for title in sorted(self.owned_titles):
            try:
                self.close_to_home()
                if self.is_element_visible(self._event_locator(title), timeout=2):
                    self.delete_event(title)
                self.assert_absent(title)
            except Exception as error:
                failures.append(f"{title}: {error}")
        if failures:
            raise AssertionError("Calendar owned-data cleanup failed: " + "; ".join(failures))
