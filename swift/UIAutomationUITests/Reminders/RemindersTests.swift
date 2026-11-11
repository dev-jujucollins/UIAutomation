import XCTest

/// Reminders overview, list navigation, discarded drafts, and one owned reminder.
/// Port of tests/integration/test_reminders.py.
final class RemindersTests: SystemAppTestCase {
    override class var bundleID: String { RemindersHome.bundleID }

    private var home: RemindersHome!

    override func setUpWithError() throws {
        try super.setUpWithError()
        home = RemindersHome(app: app)
        try home.waitUntilReady()
    }

    /// Restart Reminders so each check reads persisted data, not the current screen.
    private func relaunchedHome() throws -> RemindersHome {
        relaunch()
        try home.waitUntilReady()
        return home
    }

    /// Delete the owned title wherever it is; a completed reminder lives in Completed.
    private func deleteEverywhere(_ title: String) throws {
        let home = try relaunchedHome()
        let openers: [() throws -> ReminderList] = [
            { try home.openList() }, { try home.openCompleted() },
        ]
        for open in openers {
            let list = try open()
            if try list.state(title) != nil { try list.delete(title) }
            _ = try list.goBack()
        }
    }

    /// Reminders reaches its lists overview past first-launch screens. (smoke)
    func testRemindersHomeIsReady() throws {
        XCTAssertGreaterThanOrEqual(try home.listCount(), 0)
    }

    /// The default list opens and Back returns to the overview. (journey)
    func testOpenDefaultListAndReturn() throws {
        let list = try home.openList()
        _ = try list.goBack()
    }

    /// A typed then discarded reminder never reaches the list. (journey)
    func testDiscardedDraftCreatesNothing() throws {
        let before = try home.listCount()
        let title = "UIAutomation draft \(randomToken(8))"
        // Register the discard before opening the test-owned sheet.
        addCleanup { [app] in
            let sheet = NewReminder(app: app!)
            if sheet.isOpen { try sheet.discard() }
        }
        let draft = try home.openNewReminder()
        try draft.setTitle(title)
        try draft.discard()
        XCTAssertEqual(try home.listCount(), before)
        XCTAssertNil(try home.openList().state(title))
    }

    /// A reminder persists across relaunches, moves to Completed, and deletes cleanly.
    /// (lifecycle, regression)
    func testReminderCreateCompleteDelete() throws {
        try RunOptions.requireLifecycle()
        let title = "UIAutomation \(randomToken(12))"
        XCTAssertNil(try home.openList().state(title), "Generated title already exists")
        // Register cleanup before creating: only this exact generated title is ever deleted.
        addCleanup { try self.deleteEverywhere(title) }

        let sheet = try relaunchedHome().openNewReminder()
        try sheet.setTitle(title)
        _ = try sheet.save()

        let list = try relaunchedHome().openList()
        XCTAssertEqual(
            try list.state(title), .incomplete, "Created reminder did not survive relaunch")
        try list.complete(title)

        let completed = try relaunchedHome().openCompleted()
        XCTAssertEqual(
            try completed.state(title), .completed, "Completed reminder missing after relaunch")
        try completed.delete(title)

        XCTAssertNil(try relaunchedHome().openList().state(title))
        XCTAssertNil(try relaunchedHome().openCompleted().state(title))
    }

    // MARK: Diagnostics (opt-in)

    /// Key controls of this screen still match. (diagnostic, locators)
    func testLocatorHealth() throws {
        try RunOptions.requireDiagnostics()
        assertLocatorsFound([
            "Lists overview": home.listsNav,
            "New Reminder": home.newReminder,
            "Add List": home.addList,
            "Completed": home.completed,
        ])
    }

    /// Every control on this screen has an accessibility label. (diagnostic, accessibility)
    func testAccessibilityLabels() throws {
        try RunOptions.requireDiagnostics()
        try assertLabelled()
    }
}
