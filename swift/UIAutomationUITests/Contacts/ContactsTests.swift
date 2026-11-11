import XCTest

/// Owned Contacts lifecycle coverage on a disposable simulator.
/// Port of tests/integration/test_contacts.py.
final class ContactsTests: SystemAppTestCase {
    override class var bundleID: String { ContactsPage.bundleID }

    /// Unicode names persist across restarts, and deletion persists too.
    /// (lifecycle, regression)
    func testContactCreateReopenEditDelete() throws {
        try RunOptions.requireLifecycle()
        let contacts = ContactsPage(app: app)
        let token = randomToken(12)
        let original = ("UIAutomation", "\(token) Élise O'Connor")
        let edited = ("UIAutomation", "\(token) Zoë O'Connor")
        let originalName = ContactsPage.fullName(original.0, original.1)
        let editedName = ContactsPage.fullName(edited.0, edited.1)

        // A collision or an unrelated unsaved editor must fail before registering
        // deletion. This test may only clean up names it is about to create.
        try contacts.relaunch()
        for name in [originalName, editedName] {
            XCTAssertFalse(
                try contacts.searchContact(name), "Generated contact already exists: \(name)")
        }
        try contacts.relaunch()
        addCleanup { try contacts.cleanupOwnedContacts([originalName, editedName]) }

        try contacts.createContact(original.0, original.1)
        try contacts.relaunch()
        XCTAssertTrue(
            try contacts.searchContact(originalName), "Created contact did not survive relaunch")
        try contacts.openContact(originalName)
        try contacts.editContact(originalName, first: edited.0, last: edited.1)

        try contacts.relaunch()
        XCTAssertFalse(
            try contacts.searchContact(originalName), "Old contact name remained after rename")
        XCTAssertTrue(
            try contacts.searchContact(editedName), "Edited contact did not survive relaunch")
        try contacts.openContact(editedName)
        try contacts.deleteContact(editedName)

        try contacts.relaunch()
        XCTAssertFalse(
            try contacts.searchContact(editedName), "Deleted contact returned after relaunch")
        XCTAssertFalse(
            try contacts.searchContact(originalName), "Original contact remained after lifecycle")
    }

    // MARK: Diagnostics (opt-in)

    /// Key controls of the contact list still match. (diagnostic, locators)
    func testLocatorHealth() throws {
        try RunOptions.requireDiagnostics()
        let contacts = ContactsPage(app: app)
        try contacts.relaunch()
        assertLocatorsFound([
            "Search field": contacts.searchField,
            "Add button": contacts.addButton,
        ])
    }

    /// Every control on the contact list has an accessibility label.
    /// (diagnostic, accessibility)
    func testAccessibilityLabels() throws {
        try RunOptions.requireDiagnostics()
        try ContactsPage(app: app).relaunch()
        try assertLabelled()
    }
}
