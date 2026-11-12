import XCTest

/// Messages conversation list and native compose entry point.
/// Port of src/uiautomation/pages/messages/messages_home.py.
@MainActor
struct MessagesHome {
    nonisolated static let bundleID = "com.apple.MobileSMS"

    let app: XCUIApplication

    var navigationBar: XCUIElement { app.navigationBars["Messages"].firstMatch }
    var searchField: XCUIElement { app.element("Search") }
    var conversationList: XCUIElement { app.collectionViews["ConversationList"].firstMatch }

    /// Require the home navigation, search field, and conversation list.
    func waitUntilReady() throws {
        guard navigationBar.waitForVisible(), searchField.waitForVisible(),
              conversationList.appears(timeout: 10)
        else {
            throw PageError("Messages home not ready")
        }
    }

    /// Open an empty native composer through the sms: URL handler.
    func openCompose() throws -> ComposeMessage {
        try waitUntilReady()
        app.open(URL(string: "sms:")!)
        let page = ComposeMessage(app: app)
        try page.waitUntilReady()
        return page
    }

    /// Open a seeded conversation; fail explicitly if test data is missing.
    func openFirstConversation() throws -> Conversation {
        try waitUntilReady()
        let rows = conversationList.children(matching: .cell).allElementsBoundByIndex
        guard let row = rows.first(where: \.isVisible) else {
            throw PageError("Messages requires a seeded conversation on the test simulator")
        }
        row.tap()
        let page = Conversation(app: app)
        try page.waitUntilReady()
        return page
    }
}

/// Native Messages composer with explicit unsent-draft cleanup. Nothing here sends.
/// Port of src/uiautomation/pages/messages/compose_message.py.
@MainActor
struct ComposeMessage {
    let app: XCUIApplication

    var navigationBar: XCUIElement { app.navigationBars["CKComposeChat"].firstMatch }
    var recipientField: XCUIElement { app.element("To:") }
    var bodyField: XCUIElement { app.element("messageBodyField") }
    var cancelButton: XCUIElement { navigationBar.buttons["Cancel"].firstMatch }

    var isOpen: Bool { navigationBar.exists }

    /// Require the native compose sheet and its editable fields.
    func waitUntilReady() throws {
        guard navigationBar.waitForVisible(), recipientField.waitForVisible(),
              bodyField.waitForVisible(), cancelButton.waitForVisible()
        else {
            throw PageError("Messages composer not ready")
        }
    }

    /// Uncommitted recipient text from the To field.
    var recipient: String { recipientField.textValue }
    /// The current unsent message text.
    var body: String { bodyField.textValue }

    /// Replace recipient text without committing or sending a message.
    func setRecipient(_ recipient: String) throws {
        try replace(recipientField, with: recipient)
    }

    /// Replace draft text, including Unicode and newlines, and wait for the field to show it.
    func setBody(_ text: String) throws {
        try replace(bodyField, with: text)
    }

    private func replace(_ field: XCUIElement, with text: String) throws {
        guard field.waitForVisible() else { throw PageError("Messages field not editable") }
        field.replaceText(with: text)
        try waitUntil("Messages field never showed the typed text") { field.textValue == text }
    }

    /// Clear this test's draft before closing; safe to call after cancellation.
    @discardableResult
    func discard() throws -> MessagesHome {
        if isOpen {
            try setBody("")
            try setRecipient("")
            cancelButton.tap()
            try waitUntil("Messages composer did not close") { !isOpen }
        }
        let home = MessagesHome(app: app)
        try home.waitUntilReady()
        return home
    }
}

/// Read-only navigation within an existing Messages conversation.
/// Port of src/uiautomation/pages/messages/conversation.py.
@MainActor
struct Conversation {
    let app: XCUIApplication

    var title: XCUIElement { app.element("ConversationTitle") }
    var bodyField: XCUIElement { app.element("messageBodyField") }
    var backButton: XCUIElement { app.buttons["BackButton"].firstMatch }
    var transcript: XCUIElement { app.element("TranscriptCollectionView") }

    func waitUntilReady() throws {
        guard title.waitForVisible(), bodyField.waitForVisible(), backButton.waitForVisible(),
              transcript.appears(timeout: 10)
        else {
            throw PageError("Messages conversation not ready")
        }
    }

    /// The conversation header's displayed recipient.
    func recipient() throws -> String {
        let value = title.label
        guard !value.trimmingCharacters(in: .whitespaces).isEmpty else {
            throw PageError("Conversation recipient is empty")
        }
        return value
    }

    /// Return to Messages home and wait for the transition to finish.
    @discardableResult
    func goBack() throws -> MessagesHome {
        backButton.tap()
        try waitUntil("Conversation did not close") { !bodyField.exists }
        let home = MessagesHome(app: app)
        try home.waitUntilReady()
        return home
    }
}
