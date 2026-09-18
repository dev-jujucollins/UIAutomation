"""Messages conversation list and native compose entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...drivers.ios_driver import SystemApps
from ..base_page import BasePage

if TYPE_CHECKING:
    from .compose_message import ComposeMessagePage
    from .conversation import ConversationPage


class MessagesHomePage(BasePage):
    """Navigate the simulator's Messages home using live accessibility controls."""

    NAVIGATION_BAR = (
        BasePage.By.IOS_CLASS_CHAIN,
        '**/XCUIElementTypeNavigationBar[`name == "Messages"`]',
    )
    SEARCH_FIELD = (BasePage.By.ACCESSIBILITY_ID, "Search")
    CONVERSATION_LIST = (BasePage.By.ACCESSIBILITY_ID, "ConversationList")
    CONVERSATION_ROWS = (
        BasePage.By.IOS_CLASS_CHAIN,
        '**/XCUIElementTypeCollectionView[`name == "ConversationList"`]/XCUIElementTypeCell',
    )

    def wait_until_ready(self) -> None:
        """Require the home navigation, search field, and conversation list."""
        self.wait_for_visible(self.NAVIGATION_BAR)
        self.wait_for_visible(self.SEARCH_FIELD)
        self.find_element(self.CONVERSATION_LIST)

    def open_compose(self) -> ComposeMessagePage:
        """Open an empty native composer through the simulator's sms URL handler."""
        from .compose_message import ComposeMessagePage

        self.wait_until_ready()
        self.driver.execute_script(
            "mobile: deepLink", {"url": "sms:", "bundleId": SystemApps.MESSAGES.value}
        )
        page = ComposeMessagePage(self.driver)
        page.wait_until_ready()
        return page

    def open_first_conversation(self) -> ConversationPage:
        """Open a seeded conversation; fail explicitly if test data is missing."""
        from .conversation import ConversationPage

        self.wait_until_ready()
        rows = self.driver.find_elements(*self.CONVERSATION_ROWS)
        visible_rows = [row for row in rows if row.is_displayed()]
        if not visible_rows:
            raise AssertionError("Messages requires a seeded conversation on the test simulator")
        visible_rows[0].click()
        page = ConversationPage(self.driver)
        page.wait_until_ready()
        return page
