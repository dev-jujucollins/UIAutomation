import XCTest

/// Calendar navigation, event drafts, the calendars list, onboarding, and one owned event.
/// Port of tests/integration/test_calendar.py and test_calendar_lifecycle.py. The
/// account-names case needs a physical iPhone with a calendar account and is not ported.
final class CalendarTests: SystemAppTestCase {
    override class var bundleID: String { CalendarHome.bundleID }

    private var home: CalendarHome!

    override func setUpWithError() throws {
        try super.setUpWithError()
        home = CalendarHome(app: app)
        // Location, notification and contacts prompts, and What's New, on first launch.
        XCTAssertTrue(
            try home.dismissAllOnboarding(timeout: CalendarHome.launchTimeout),
            "Failed to dismiss Calendar onboarding")
        XCTAssertTrue(home.isOnCalendarHome, "Failed to reach Calendar home")
    }

    /// Own one Calendar editor, registering its discard before opening it.
    private func draft() throws -> NewEvent {
        addCleanup { [app] in try NewEvent(app: app!).discard() }
        return try home.tapAddEvent()
    }

    // MARK: Navigation

    /// Calendar launches. (smoke)
    func testCalendarAppLaunches() throws {
        XCTAssertTrue(home.isOnCalendarHome)
    }

    func testCurrentMonthDisplayed() throws {
        try home.tapToday()
        XCTAssertEqual(try home.selectedDate(), Day.today)
        XCTAssertEqual(home.currentMonth(), CalendarHome.months[Day.today.month - 1])
    }

    func testTapToday() throws {
        try home.tapToday()
        let other = try home.selectAnotherVisibleDay()
        XCTAssertNotEqual(other, Day.today)
        try home.tapToday()
        XCTAssertTrue(try home.isTodaySelected())
    }

    /// Day-to-month navigation and an explicit return to day view. (journey)
    func testNavigateToMonthView() throws {
        if home.isOnMonthView(timeout: 1) { try home.tapToday() }
        XCTAssertTrue(home.dayViewNavBar.waitForVisible())
        home.tapBackToMonth()
        XCTAssertTrue(home.isOnMonthView())
        try home.tapToday()
        XCTAssertTrue(home.dayViewNavBar.waitForVisible())
    }

    // MARK: Event drafts

    /// The new event sheet opens and Cancel closes it. (journey)
    func testOpenNewEvent() throws {
        let editor = try draft()
        XCTAssertTrue(editor.isOnNewEventPage)
        let home = try editor.tapCancel()
        XCTAssertFalse(editor.titleField.exists)
        XCTAssertTrue(home.isOnCalendarHome)
    }

    /// Title editing, then return home without saving the draft. (journey)
    func testEditAndCancelEventDraft() throws {
        let editor = try draft()
        for title in ["Test Meeting", "Revised Test Meeting"] {
            try editor.setTitle(title)
            XCTAssertEqual(editor.title, title, "Draft title did not match")
        }
        XCTAssertTrue(editor.isDoneEnabled, "Edited draft cannot be saved")
        let home = try editor.tapCancel()
        XCTAssertFalse(editor.titleField.exists)
        XCTAssertTrue(home.isOnCalendarHome, "Cancel did not restore Calendar home")
    }

    func testToggleAllDay() throws {
        let editor = try draft()
        let initial = try editor.isAllDayEnabled()
        try editor.toggleAllDay()
        XCTAssertNotEqual(try editor.isAllDayEnabled(), initial)
        try editor.tapCancel()
    }

    func testEventReminderTabs() throws {
        let editor = try draft()
        XCTAssertTrue(editor.isEventTabSelected, "Event tab should be selected by default")
        editor.reminderTab.tap()
        XCTAssertFalse(editor.isEventTabSelected)
        editor.eventTab.tap()
        XCTAssertTrue(editor.isEventTabSelected)
        try editor.tapCancel()
    }

    // MARK: Calendars list

    func testOpenCalendarsList() throws {
        let calendars = try home.tapCalendars()
        XCTAssertTrue(calendars.isOnCalendarsList)
        try calendars.tapDone()
    }

    func testGetCalendarNames() throws {
        let calendars = try home.tapCalendars()
        XCTAssertFalse(calendars.calendarNames().isEmpty, "Expected at least one calendar")
        try calendars.tapDone()
    }

    // MARK: Diagnostics and onboarding

    /// Informational: lists visible events; there may be none. (diagnostic)
    func testGetDatesWithEvents() throws {
        try RunOptions.requireDiagnostics()
        print("Dates with events: \(home.visibleDatesWithEvents())")
    }

    /// Onboarding screens can be dismissed to reach the main Calendar. To exercise the
    /// first-launch prompts themselves, erase the simulator before running. (onboarding)
    func testOnboardingDismissalReachesHome() throws {
        relaunch()
        XCTAssertTrue(try home.dismissAllOnboarding())
        XCTAssertTrue(home.isOnCalendarHome)
    }

    // MARK: Lifecycle

    /// Persist, reopen, rename, reopen again, delete, and verify the owned event is gone.
    /// (lifecycle, journey)
    func testCalendarEventLifecycle() throws {
        try RunOptions.requireLifecycle()
        let original = "UIAutomation Event \(randomToken(32))"
        let edited = "\(original) edited"
        // Both possible saved titles are registered for cleanup before anything is created.
        let events = CalendarEvents(app: app, ownedTitles: [original, edited])
        addCleanup { try events.cleanup() }

        try events.createAllDay(original)
        try events.relaunch()
        try events.openEvent(original)
        try events.renameEvent(original, to: edited)
        try events.relaunch()
        try events.openEvent(edited)
        try events.deleteEvent(edited)
        try events.relaunch()
        try events.assertAbsent(original)
        try events.assertAbsent(edited)
    }

    // MARK: Diagnostics (opt-in)

    /// Key controls of Calendar home still match. (diagnostic, locators)
    func testHomeLocatorHealth() throws {
        try RunOptions.requireDiagnostics()
        assertLocatorsFound([
            "Day view": home.dayViewNavBar,
            "Toolbar": home.toolbar,
            "Today button": home.todayButton,
            "Add button": home.addButton,
            "Calendars button": home.calendarsButton,
            "Inbox button": home.inboxButton,
            "Search button": home.searchButton,
            "Current day label": home.currentDayLabel,
            "Day/list toggle": home.toggleViewButton,
        ])
    }

    /// Key controls of the event editor still match. (diagnostic, locators)
    func testEditorLocatorHealth() throws {
        try RunOptions.requireDiagnostics()
        let editor = try draft()
        XCTAssertTrue(editor.isOnNewEventPage)
        assertLocatorsFound([
            "Sheet title": editor.newTitle,
            "Title field": editor.titleField,
            "Cancel button": editor.cancelButton,
            "Add/Done button": editor.addDoneButton,
            "Location field": editor.locationField,
        ])
    }

    /// Every control on Calendar home has an accessibility label. (diagnostic, accessibility)
    func testHomeAccessibilityLabels() throws {
        try RunOptions.requireDiagnostics()
        try assertLabelled()
    }

    /// Every control in the event editor has an accessibility label.
    /// (diagnostic, accessibility)
    func testEditorAccessibilityLabels() throws {
        try RunOptions.requireDiagnostics()
        let editor = try draft()
        XCTAssertTrue(editor.isOnNewEventPage)
        try assertLabelled()
    }
}
