import XCTest

/// Contacts search and exact-name lifecycle actions for isolated simulators, using the
/// English iOS 27 Contacts UI.
/// Port of src/uiautomation/pages/contacts/contacts_page.py.
@MainActor
struct ContactsPage {
    nonisolated static let bundleID = "com.apple.MobileAddressBook"

    let app: XCUIApplication

    var searchField: XCUIElement { app.searchFields["Search"].firstMatch }
    var addButton: XCUIElement { app.buttons["Add"].firstMatch }
    var firstName: XCUIElement { app.element("First name") }
    var lastName: XCUIElement { app.element("Last name") }
    var doneButton: XCUIElement { app.buttons["Done"].firstMatch }
    var closeButton: XCUIElement { app.buttons["close"].firstMatch }
    var editButton: XCUIElement { app.buttons["Edit"].firstMatch }
    var backButton: XCUIElement { app.buttons["BackButton"].firstMatch }
    var header: XCUIElement { app.element("ContactCardHeaderView") }
    var deleteRow: XCUIElement { app.cells["Delete Contact"].firstMatch }
    var discardSheet: XCUIElement {
        app.sheets.matching(
            NSPredicate(
                format: "identifier IN %@ OR label IN %@",
                Self.discardTitles, Self.discardTitles)
        ).firstMatch
    }

    private static let discardTitles = [
        "Are you sure you want to discard this new contact?",
        "Are you sure you want to discard your changes?",
    ]

    /// Require the contact list's Search and Add controls.
    func waitUntilReady() throws {
        guard searchField.waitForVisible(), addButton.waitForVisible() else {
            throw PageError("Contacts list not ready")
        }
    }

    /// Restart Contacts and reach its list, optionally discarding an owned editor.
    ///
    /// - Parameter discardOwnedEditor: Allow cleanup to discard an editor opened by this
    ///   test, after the initial list state was verified.
    func relaunch(discardOwnedEditor: Bool = false) throws {
        app.launch()
        if doneButton.waitForVisible(timeout: 1) {
            guard discardOwnedEditor else {
                throw PageError("Contacts opened with an unsaved editor; refusing to discard it")
            }
            try discardEditor()
        }
        if editButton.waitForVisible(timeout: 1) { backButton.tap() }
        guard searchField.waitForVisible() else { throw PageError("Contacts search not shown") }
        if !addButton.waitForVisible(timeout: 1) { closeButton.tap() }
        try waitUntilReady()
    }

    /// The expected English display name; both parts are required for lifecycle contacts.
    static func fullName(_ first: String, _ last: String) -> String {
        precondition(
            !first.trimmingCharacters(in: .whitespaces).isEmpty
                && !last.trimmingCharacters(in: .whitespaces).isEmpty,
            "Both first and last names are required for lifecycle contacts")
        return "\(first) \(last)"
    }

    /// Exact contact cells on screen, excluding hidden backing-list cells retained while
    /// search is active.
    private func visibleRows(_ fullName: String) -> [XCUIElement] {
        app.cells.matching(identifier: fullName).allElementsBoundByIndex.filter(\.isVisible)
    }

    /// Require the exact saved name before modifying a contact.
    func assertContactName(_ expected: String) throws {
        try waitUntil("Contact card never showed '\(expected)'") {
            header.exists && header.label == expected
        }
        guard editButton.waitForVisible() else { throw PageError("Contact card has no Edit") }
    }

    /// Replace names and confirm the fields kept the supplied Unicode text.
    private func setNames(_ first: String, _ last: String) throws {
        _ = Self.fullName(first, last)
        for (field, text) in [(firstName, first), (lastName, last)] {
            guard field.waitForVisible() else { throw PageError("Contact name field missing") }
            field.tap()
            field.replaceText(with: text)
            try waitUntil("Contact field never showed '\(text)'") { field.textValue == text }
        }
    }

    /// Create a named contact and verify the saved detail card.
    func createContact(_ first: String, _ last: String) throws {
        try waitUntilReady()
        addButton.tap()
        try setNames(first, last)
        doneButton.tap()
        try assertContactName(Self.fullName(first, last))
    }

    /// Rename only the exact currently open contact and verify the saved name.
    func editContact(_ expected: String, first: String, last: String) throws {
        try assertContactName(expected)
        editButton.tap()
        try setNames(first, last)
        doneButton.tap()
        try assertContactName(Self.fullName(first, last))
    }

    /// Search and open exactly one visible matching contact, rejecting ambiguity.
    func openContact(_ fullName: String) throws {
        guard try searchContact(fullName) else { throw PageError("Contact not found: \(fullName)") }
        let rows = visibleRows(fullName)
        guard rows.count == 1 else {
            throw PageError("Expected one visible contact named '\(fullName)'; found \(rows.count)")
        }
        rows[0].tap()
        try assertContactName(fullName)
    }

    /// Wait for an exact contact search result or the native empty-results state.
    func searchContact(_ fullName: String) throws -> Bool {
        precondition(
            !fullName.trimmingCharacters(in: .whitespaces).isEmpty,
            "Contact search requires an exact nonempty name")
        guard searchField.waitForVisible() else { throw PageError("Contacts search not shown") }
        searchField.tap()
        searchField.replaceText(with: fullName)
        try waitUntil("Contacts search never showed '\(fullName)'") {
            searchField.textValue == fullName
        }
        // The query-specific empty state, so stale results from an earlier search don't count.
        let noResults = app.staticTexts["No Results for “\(fullName)”"].firstMatch
        try waitUntil("Contacts search did not settle for '\(fullName)'") {
            !visibleRows(fullName).isEmpty || noResults.isVisible
        }
        let rows = visibleRows(fullName)
        guard rows.count <= 1 else {
            throw PageError("Multiple visible contacts named '\(fullName)'; refusing to choose")
        }
        return !rows.isEmpty
    }

    /// Delete the exact open contact through its editor and native confirmation.
    func deleteContact(_ expected: String) throws {
        try assertContactName(expected)
        editButton.tap()
        guard firstName.waitForVisible() else { throw PageError("Contact editor did not open") }
        guard Self.fullName(firstName.textValue, lastName.textValue) == expected else {
            throw PageError("Contact editor identity changed; refusing to delete")
        }
        for attempt in 0..<7 {
            if deleteRow.waitForVisible(timeout: 1) { break }
            guard attempt < 6 else { throw PageError("Delete Contact row did not become visible") }
            app.swipeUp()
        }
        deleteRow.tap()

        let sheet = app.sheets.firstMatch
        guard sheet.waitForVisible() else { throw PageError("No delete confirmation sheet") }
        // Searched only inside the confirmation sheet. iOS 27.2 renamed the button to
        // "Delete" and gave the sheet itself the "Delete Contact" name.
        let buttons = sheet.buttons.matching(
            NSPredicate(format: "label IN %@", ["Delete Contact", "Delete"])
        ).allElementsBoundByIndex
        guard buttons.count == 1 else {
            throw PageError("Expected exactly one Delete Contact button in the confirmation")
        }
        // iOS 27 can report this button as not hittable while its sheet is on screen.
        buttons[0].tapEvenIfNotHittable()
        guard searchField.waitForVisible() else {
            throw PageError("Contacts list did not return after deleting")
        }
        if try searchContact(expected) {
            throw PageError("Deleted contact is still present: \(expected)")
        }
    }

    /// Discard only an editor opened after the test established a clean list.
    private func discardEditor() throws {
        closeButton.tap()
        try waitUntil("Contacts editor did not close or present its discard confirmation") {
            discardSheet.exists || !doneButton.isVisible
        }
        if discardSheet.exists {
            discardSheet.buttons["Discard Changes"].firstMatch.tapEvenIfNotHittable()
        }
        try waitUntil("Contacts editor did not close") { !doneButton.isVisible }
    }

    /// Attempt every exact owned name and report cleanup failures together.
    func cleanupOwnedContacts(_ names: [String]) throws {
        var errors: [String] = []
        var seen = Set<String>()
        for name in names where seen.insert(name).inserted {
            do {
                try relaunch(discardOwnedEditor: true)
                if try searchContact(name) {
                    try openContact(name)
                    try deleteContact(name)
                }
            } catch {
                errors.append("'\(name)': \(error)")
            }
        }
        if !errors.isEmpty {
            throw PageError("Contacts cleanup failed: " + errors.joined(separator: "; "))
        }
    }
}
