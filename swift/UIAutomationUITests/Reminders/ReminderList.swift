import XCTest

enum ReminderState: String {
    case incomplete = "Incomplete"
    case completed = "Completed"
}

/// One Reminders list and its rows.
/// Rows are cells labelled "<title>, Incomplete" or "<title>, Completed[, in <list>]".
/// Port of src/uiautomation/pages/reminders/reminder_list.py.
@MainActor
struct ReminderList {
    let app: XCUIApplication
    let name: String

    var navigationBar: XCUIElement { app.navigationBars[name].firstMatch }
    var backButton: XCUIElement { app.buttons["BackButton"].firstMatch }

    func waitUntilReady() throws {
        guard navigationBar.appears(timeout: 10),
              backButton.appears(timeout: 10)
        else {
            throw PageError("Reminders list '\(name)' did not open")
        }
    }

    func row(_ title: String) -> XCUIElement {
        app.cells.matching(NSPredicate(format: "label BEGINSWITH %@", title + ", ")).firstMatch
    }

    /// The row's state, or nil when the reminder is not in this list.
    func state(_ title: String) throws -> ReminderState? {
        let row = row(title)
        guard row.exists else { return nil }
        let rest = row.label.dropFirst(title.count + 2)
        let raw = rest.components(separatedBy: ", ").first ?? ""
        guard let state = ReminderState(rawValue: raw) else {
            throw PageError("Unexpected reminder row label for '\(title)': \(raw)")
        }
        return state
    }

    func waitForState(_ title: String, _ expected: ReminderState?) throws {
        let wanted = expected?.rawValue ?? "absent"
        try waitUntil("'\(title)' never became \(wanted)") {
            try state(title) == expected
        }
    }

    /// Tick the reminder once; Reminders moves it to Completed a few seconds later.
    func complete(_ title: String) throws {
        guard try state(title) == .incomplete else {
            throw PageError("'\(title)' is not an incomplete reminder in \(name)")
        }
        row(title).descendants(matching: .any).matching(identifier: "Circle").firstMatch.tap()
        try waitForState(title, .completed)
    }

    /// Swipe the row left and tap Delete; Reminders deletes without confirming.
    func delete(_ title: String) throws {
        let row = row(title)
        guard row.exists else { throw PageError("No reminder '\(title)' in \(name)") }
        row.swipeLeft()
        let delete = app.buttons["Delete"].firstMatch
        guard delete.appears(timeout: 10) else {
            throw PageError("No Delete action for '\(title)'")
        }
        delete.tap()
        try waitForState(title, nil)
    }

    func goBack() throws -> RemindersHome {
        backButton.tap()
        let home = RemindersHome(app: app)
        try home.waitUntilReady()
        return home
    }
}
