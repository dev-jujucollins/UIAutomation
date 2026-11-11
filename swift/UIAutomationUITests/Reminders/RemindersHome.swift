import XCTest

/// Reminders lists overview: smart lists (Today, Scheduled, All, Completed) and My Lists.
/// Port of src/uiautomation/pages/reminders/reminders_home.py.
@MainActor
struct RemindersHome {
    nonisolated static let bundleID = "com.apple.reminders"
    nonisolated static let defaultList = "Reminders"
    nonisolated static let launchTimeout: TimeInterval = 30

    let app: XCUIApplication

    var listsNav: XCUIElement { app.element("Reminders.TTRIAccountsListsView") }
    var newReminder: XCUIElement { app.buttons["New Reminder"].firstMatch }
    var addList: XCUIElement { app.buttons["Add List"].firstMatch }
    var listsTable: XCUIElement { app.element("AccountsList.ID.AccountsListTable") }
    var completed: XCUIElement { app.element("Completed") }
    var backButton: XCUIElement { app.buttons["BackButton"].firstMatch }
    // First-launch "Welcome to Reminders" screen.
    var welcomeTitle: XCUIElement { app.element("Welcome to Reminders") }
    var welcomeContinue: XCUIElement { app.buttons["Continue"].firstMatch }

    /// Get past first-launch screens and any restored list to the overview.
    /// Reminders reopens the screen it was last on, so a list view is left with Back.
    func waitUntilReady() throws {
        try waitUntil(timeout: Self.launchTimeout, "Reminders lists overview not ready") {
            if try SystemPrompts.answer(in: app, context: "Reminders") { return false }
            if welcomeTitle.exists {
                if welcomeContinue.exists { welcomeContinue.tap() }
                return false
            }
            if listsNav.exists {
                return newReminder.exists && addList.exists
            }
            if backButton.exists { backButton.tap() }
            return false
        }
    }

    /// A list under My Lists; its label is "<name>, <n> reminder(s)".
    func listCell(_ name: String) -> XCUIElement {
        app.cells.matching(NSPredicate(format: "label BEGINSWITH %@", name + ", ")).firstMatch
    }

    /// My Lists sits below the smart lists; at large text sizes it starts off screen,
    /// and off-screen cells are not in the accessibility tree.
    func scrollToList(_ name: String, maxSwipes: Int = 5) throws -> XCUIElement {
        let cell = listCell(name)
        for _ in 0..<maxSwipes where !cell.exists {
            listsTable.swipeUp()
        }
        guard cell.exists else {
            throw PageError("Reminders list '\(name)' not found after \(maxSwipes) swipes")
        }
        return cell
    }

    /// Number of incomplete reminders the overview reports for a list.
    func listCount(_ name: String = defaultList) throws -> Int {
        let label = try scrollToList(name).label
        let prefix = name + ", "
        let parts = label.dropFirst(prefix.count).split(separator: " ")
        guard label.hasPrefix(prefix), parts.count == 2,
              let count = Int(parts[0]),
              parts[1] == "reminder" || parts[1] == "reminders"
        else {
            throw PageError("Unexpected list label: \(label)")
        }
        return count
    }

    /// Open the New Reminder sheet.
    func openNewReminder() throws -> NewReminder {
        newReminder.tap()
        let sheet = NewReminder(app: app)
        try sheet.waitUntilReady()
        return sheet
    }

    /// Open a list under My Lists.
    func openList(_ name: String = defaultList) throws -> ReminderList {
        try scrollToList(name).tap()
        let list = ReminderList(app: app, name: name)
        try list.waitUntilReady()
        return list
    }

    /// Open the Completed smart list, where finished reminders move.
    func openCompleted() throws -> ReminderList {
        completed.tap()
        let list = ReminderList(app: app, name: "Completed")
        try list.waitUntilReady()
        return list
    }
}
