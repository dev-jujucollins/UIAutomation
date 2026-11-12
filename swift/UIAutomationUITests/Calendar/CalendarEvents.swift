import XCTest

/// Create, reopen, rename and delete events whose titles this run owns.
/// Port of src/uiautomation/pages/calendar/events.py.
@MainActor
final class CalendarEvents {
    let app: XCUIApplication
    let home: CalendarHome
    let ownedTitles: Set<String>
    private var pendingDelete: String?

    init(app: XCUIApplication, ownedTitles: [String]) {
        precondition(
            !ownedTitles.isEmpty
                && ownedTitles.allSatisfy { !$0.trimmingCharacters(in: .whitespaces).isEmpty },
            "Calendar lifecycle requires non-empty owned titles")
        self.app = app
        self.home = CalendarHome(app: app)
        self.ownedTitles = Set(ownedTitles)
    }

    private var detailsTitle: XCUIElement { app.element("event-details-title-text") }
    private var editButton: XCUIElement { app.element("event-details-edit-button") }
    private var deleteButton: XCUIElement { app.element("delete-event-cell") }
    private var deleteSheet: XCUIElement {
        let title = "Are you sure you want to delete this event?"
        return app.sheets.matching(NSPredicate(format: "identifier == %@ OR label == %@", title, title))
            .firstMatch
    }
    private var editor: NewEvent { NewEvent(app: app) }

    private func event(_ title: String) throws -> XCUIElement {
        guard ownedTitles.contains(title) else {
            throw PageError("Calendar title is not owned by this run: \(title)")
        }
        return app.element("event-shown:\(title)")
    }

    private var homeReady: Bool {
        home.dayViewNavBar.isVisible && home.todayButton.isVisible && home.addButton.isVisible
            && !editor.titleField.exists && !detailsTitle.exists
            && !app.alerts.firstMatch.exists && !app.sheets.firstMatch.exists
    }

    func waitForHome() throws {
        try waitUntil("Calendar day view did not become ready") {
            if try SystemPrompts.answer(in: app, context: "Calendar") { return false }
            return homeReady
        }
    }

    /// Get back to the day view from any screen this page opens.
    func closeToHome() throws {
        _ = try SystemPrompts.answer(in: app, context: "Calendar")
        if deleteSheet.exists {
            guard let pendingDelete, ownedTitles.contains(pendingDelete) else {
                throw PageError("Cannot confirm an unowned Calendar deletion")
            }
            try confirmDelete()
        }
        if editor.titleField.exists || detailsTitle.isVisible {
            try editor.discard()
        }
        try waitForHome()
    }

    func createAllDay(_ title: String) throws {
        let event = try event(title)
        try closeToHome()
        try home.tapToday()
        guard !event.exists else { throw PageError("Owned event already exists: \(title)") }
        let editor = try home.tapAddEvent()
        try editor.setTitle(title)
        try editor.enableAllDay()
        try editor.tapDone()
        try waitForHome()
        guard event.waitForVisible() else { throw PageError("Created event not shown: \(title)") }
    }

    /// Restart Calendar so the next check reads saved events, not the current screen.
    func relaunch() throws {
        try closeToHome()
        app.launch()
        try closeToHome()
        try home.tapToday()
    }

    func openEvent(_ title: String) throws {
        let event = try event(title)
        try closeToHome()
        guard event.waitForVisible() else { throw PageError("Event not shown: \(title)") }
        event.tap()
        try waitUntil("Event details never showed '\(title)'") {
            detailsTitle.exists && detailsTitle.label == title
        }
    }

    func renameEvent(_ title: String, to newTitle: String) throws {
        let renamed = try event(newTitle)
        try openEvent(title)
        editButton.tap()
        try editor.setTitle(newTitle)
        try editor.tapDone()
        try closeToHome()
        guard renamed.waitForVisible() else { throw PageError("Renamed event not shown: \(newTitle)") }
        try assertAbsent(title)
    }

    private func confirmDelete() throws {
        guard let pendingDelete, ownedTitles.contains(pendingDelete) else {
            throw PageError("Cannot confirm an unowned Calendar deletion")
        }
        guard deleteSheet.appears() else { throw PageError("No delete confirmation for the event") }
        deleteSheet.descendants(matching: .any).matching(identifier: "delete-alert-button")
            .firstMatch.tapEvenIfNotHittable()
        try waitUntil("Delete confirmation did not close") { !deleteSheet.exists }
        self.pendingDelete = nil
    }

    func deleteEvent(_ title: String) throws {
        try openEvent(title)
        pendingDelete = title
        guard app.scroll(to: deleteButton) else { throw PageError("Event has no Delete row") }
        deleteButton.tap()
        try confirmDelete()
        try waitForHome()
        try assertAbsent(title)
    }

    func assertAbsent(_ title: String) throws {
        let event = try event(title)
        try waitForHome()
        try waitUntil("Event is still shown: \(title)") { !event.exists }
    }

    /// Delete every owned title that still exists and report failures together.
    func cleanup() throws {
        try closeToHome()
        try home.tapToday()
        var failures: [String] = []
        for title in ownedTitles.sorted() {
            do {
                try closeToHome()
                if try event(title).appears(timeout: 2) { try deleteEvent(title) }
                try assertAbsent(title)
            } catch {
                failures.append("\(title): \(error)")
            }
        }
        if !failures.isEmpty {
            throw PageError(
                "Calendar owned-data cleanup failed: " + failures.joined(separator: "; "))
        }
    }
}
