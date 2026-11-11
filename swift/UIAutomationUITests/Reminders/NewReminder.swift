import XCTest

/// New Reminder sheet opened from the Reminders lists overview.
/// Port of src/uiautomation/pages/reminders/new_reminder.py.
@MainActor
struct NewReminder {
    let app: XCUIApplication

    // The overview's "New Reminder" button shares the name, so match the bar itself.
    var navigationBar: XCUIElement { app.navigationBars["New Reminder"].firstMatch }
    var titleField: XCUIElement { app.element("Quick Entry Title Field") }
    var doneButton: XCUIElement { app.buttons["Done"].firstMatch }
    var cancelButton: XCUIElement { app.buttons["Cancel"].firstMatch }
    // Cancel with a typed title asks "Are you sure you want to discard this new reminder?"
    var discardButton: XCUIElement { app.buttons["Discard Changes"].firstMatch }

    var isOpen: Bool { navigationBar.exists }

    func waitUntilReady() throws {
        guard navigationBar.appears(timeout: 10),
              titleField.appears(timeout: 10)
        else {
            throw PageError("New Reminder sheet did not open")
        }
    }

    /// Type a title and wait until the field reports it.
    func setTitle(_ title: String) throws {
        // Rows are labelled "<title>, <state>"; a comma would make that ambiguous.
        precondition(!title.contains(","), "Reminder titles used by tests must not contain commas")
        titleField.tap()
        titleField.typeText(title)
        try waitUntil("Title field never showed '\(title)'") {
            titleField.value as? String == title
        }
    }

    /// Add the reminder and return to the overview.
    func save() throws -> RemindersHome {
        doneButton.tap()
        try waitUntil("New Reminder sheet did not close after Done") { !isOpen }
        return RemindersHome(app: app)
    }

    /// Cancel the sheet, confirming the discard prompt if a title was typed.
    /// Safe to call when the sheet is already closed, so it can run in tearDown.
    func discard() throws {
        var tapped = Set<String>()
        try waitUntil("New Reminder sheet did not close") {
            let controls = [("discard", discardButton), ("cancel", cancelButton)]
            for (key, button) in controls where button.isVisible {
                // Tap each control once; the sheet animates before it disappears.
                if tapped.insert(key).inserted { button.tap() }
                return false
            }
            return !isOpen
        }
        try RemindersHome(app: app).waitUntilReady()
    }
}
