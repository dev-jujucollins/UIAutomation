import XCTest

/// Messages draft and navigation tests; no test sends a message.
/// Port of tests/integration/test_messages.py.
final class MessagesTests: SystemAppTestCase {
    override class var bundleID: String { MessagesHome.bundleID }

    private static let testRecipient = "2025550123"
    private var home: MessagesHome!

    override func setUpWithError() throws {
        try super.setUpWithError()
        // Messages reopens the conversation it was last showing.
        let conversation = Conversation(app: app)
        if conversation.backButton.appears(timeout: 1) { try conversation.goBack() }
        home = MessagesHome(app: app)
        try home.waitUntilReady()
    }

    /// Register the discard before opening a test-owned, unsent compose sheet.
    private func openDraft() throws -> ComposeMessage {
        addCleanup { [app] in try ComposeMessage(app: app!).discard() }
        return try home.openCompose()
    }

    /// Messages exposes usable list and search controls. (smoke)
    func testMessagesHomeIsReady() throws {
        try home.waitUntilReady()
    }

    /// An empty composer closes completely and returns to Messages home. (smoke)
    func testOpenComposerAndCancel() throws {
        let draft = try openDraft()
        XCTAssertEqual(draft.recipient, "")
        XCTAssertEqual(draft.body, "")
        try draft.discard().waitUntilReady()
    }

    /// Recipient text can be edited and removed before committing it.
    func testEnterAndRemoveRecipient() throws {
        let draft = try openDraft()
        try draft.setRecipient(Self.testRecipient)
        XCTAssertEqual(draft.recipient, Self.testRecipient)
        try draft.setRecipient("")
        XCTAssertEqual(draft.recipient, "")
    }

    // pytest parametrizes one test over three texts; XCTest gets one method per case so
    // each reports separately.
    func testEditAndClearDraftPlain() throws { try editAndClearDraft("UIAutomation draft") }
    func testEditAndClearDraftUnicode() throws { try editAndClearDraft("UIAutomation café 🙂") }
    func testEditAndClearDraftMultiline() throws { try editAndClearDraft("First line\nSecond line") }

    /// Draft editing preserves entered characters and clears to empty.
    private func editAndClearDraft(_ text: String) throws {
        let draft = try openDraft()
        try draft.setBody(text)
        XCTAssertEqual(draft.body, text)
        try draft.setBody("Replacement draft")
        XCTAssertEqual(draft.body, "Replacement draft")
        try draft.setBody("")
        XCTAssertEqual(draft.body, "")
    }

    /// Discard recipient and text, then verify a reopened composer is empty. (journey)
    func testDraftDiscardRoundTrip() throws {
        let draft = try openDraft()
        try draft.setRecipient(Self.testRecipient)
        try draft.setBody("UIAutomation unsent draft")
        XCTAssertEqual(draft.body, "UIAutomation unsent draft")
        try draft.discard()

        let reopened = try home.openCompose()
        XCTAssertEqual(reopened.recipient, "")
        XCTAssertEqual(reopened.body, "")
        try reopened.discard()
    }

    /// Open simulator seed data and return without modifying its draft. (journey)
    func testExistingConversationRoundTrip() throws {
        let conversation = try home.openFirstConversation()
        XCTAssertFalse(try conversation.recipient().isEmpty)
        try conversation.goBack().waitUntilReady()
    }

    // MARK: Diagnostics (opt-in)

    /// Key controls of Messages home still match. (diagnostic, locators)
    func testHomeLocatorHealth() throws {
        try RunOptions.requireDiagnostics()
        assertLocatorsFound([
            "Navigation bar": home.navigationBar,
            "Search field": home.searchField,
            "Conversation list": home.conversationList,
        ])
    }

    /// Key controls of the composer still match. (diagnostic, locators)
    func testComposeLocatorHealth() throws {
        try RunOptions.requireDiagnostics()
        let draft = try openDraft()
        assertLocatorsFound([
            "Navigation bar": draft.navigationBar,
            "To field": draft.recipientField,
            "Message field": draft.bodyField,
            "Cancel button": draft.cancelButton,
        ])
    }

    /// Every control on Messages home has an accessibility label. (diagnostic, accessibility)
    func testHomeAccessibilityLabels() throws {
        try RunOptions.requireDiagnostics()
        try assertLabelled()
    }

    /// Every control in the composer has an accessibility label. (diagnostic, accessibility)
    func testComposeAccessibilityLabels() throws {
        try RunOptions.requireDiagnostics()
        _ = try openDraft()
        try assertLabelled()
    }
}
