import XCTest

/// A calendar day without a time, as Calendar's labels show it.
struct Day: Equatable, CustomStringConvertible {
    let year: Int
    let month: Int
    let day: Int

    var description: String { String(format: "%04d-%02d-%02d", year, month, day) }

    /// Today on the device. A simulator uses the Mac's clock and time zone, and so does
    /// the test runner (the Python suite asks Appium for the device time instead).
    static var today: Day {
        let parts = Calendar.current.dateComponents([.year, .month, .day], from: Date())
        return Day(year: parts.year!, month: parts.month!, day: parts.day!)
    }
}

/// Calendar home (day view with its toolbar), month view, and first-launch prompts.
/// Port of src/uiautomation/pages/calendar/calendar_home.py and calendar_onboarding.py.
@MainActor
struct CalendarHome {
    nonisolated static let bundleID = "com.apple.mobilecal"
    /// A cold first launch on a new or busy simulator exceeds the default 10 s wait.
    nonisolated static let launchTimeout: TimeInterval = 30
    nonisolated static let months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    let app: XCUIApplication

    var monthViewNavBar: XCUIElement { app.navigationBars["MonthViewContainerView"].firstMatch }
    var dayViewNavBar: XCUIElement { app.navigationBars["DayViewContainerView"].firstMatch }
    /// Labelled with the current month name, in the top-left corner of day view.
    var backButton: XCUIElement { dayViewNavBar.buttons.element(boundBy: 0) }
    var toggleViewButton: XCUIElement { app.element("toggle-day-list-view") }
    var searchButton: XCUIElement { app.element("searchbar-button") }
    var addButton: XCUIElement { app.element("add-plus-button") }
    var currentDayLabel: XCUIElement { app.element("current-day") }
    var todayButton: XCUIElement { app.element("today-button") }
    var calendarsButton: XCUIElement { app.element("calendars-button") }
    var inboxButton: XCUIElement { app.element("inbox-button") }
    var toolbar: XCUIElement { app.element("Toolbar") }

    // iOS 27 adds a "What’s New in Calendar" sheet on first launch.
    private var whatsNewTitle: XCUIElement {
        app.staticTexts.matching(NSPredicate(format: "label ENDSWITH %@", "New in Calendar"))
            .firstMatch
    }

    /// Decline one known system prompt or continue past the What's New sheet.
    /// Any other alert fails the test so new UI is inspected, not tapped through.
    func dismissKnownPrompt() throws -> Bool {
        if try SystemPrompts.answer(in: app, context: "Calendar") { return true }
        if whatsNewTitle.isVisible {
            app.buttons["Continue"].firstMatch.tap()
            return true
        }
        return false
    }

    /// Dismiss known first-launch prompts until Calendar home is visible.
    /// Returns false if home never appears; throws on an unrecognized alert.
    func dismissAllOnboarding(timeout: TimeInterval = 10) throws -> Bool {
        do {
            try waitUntil(timeout: timeout, "") {
                if try dismissKnownPrompt() { return false }
                return toolbar.isVisible || dayViewNavBar.isVisible
            }
            return true
        } catch let error as PageError where error.description.isEmpty {
            return false
        }
    }

    var isOnCalendarHome: Bool {
        (try? waitUntil("") { toolbar.isVisible || dayViewNavBar.isVisible }) != nil
    }

    /// Identify month view by its own navigation bar, not the shared toolbar.
    func isOnMonthView(timeout: TimeInterval = 10) -> Bool {
        monthViewNavBar.waitForVisible(timeout: timeout)
    }

    /// The displayed month's full name, from the current-day label.
    func currentMonth() -> String? {
        guard currentDayLabel.appears() else { return nil }
        let label = currentDayLabel.label
        return Self.months.first { label.contains($0.prefix(3)) }
    }

    /// Parse the English current-day label, rejecting incomplete dates.
    static func parseSelectedDate(_ label: String) throws -> Day {
        for (index, month) in months.enumerated() {
            let pattern = #"\b(?:\#(month)|\#(month.prefix(3)))\s+(\d{1,2}),?\s+(\d{4})\b"#
            guard let regex = try? NSRegularExpression(pattern: pattern),
                  let match = regex.firstMatch(
                    in: label, range: NSRange(label.startIndex..., in: label)),
                  let day = Range(match.range(at: 1), in: label).flatMap({ Int(label[$0]) }),
                  let year = Range(match.range(at: 2), in: label).flatMap({ Int(label[$0]) })
            else { continue }
            return Day(year: year, month: index + 1, day: day)
        }
        throw PageError("Unrecognized Calendar date label: \(label)")
    }

    /// The displayed day, read from the label rather than from a Today control.
    func selectedDate() throws -> Day {
        guard currentDayLabel.appears() else {
            throw PageError("Calendar current-day control is missing")
        }
        return try Self.parseSelectedDate(currentDayLabel.label)
    }

    func isTodaySelected() throws -> Bool { try selectedDate() == Day.today }

    /// Navigate to today's date.
    func tapToday() throws {
        guard todayButton.waitForVisible() else { throw PageError("Calendar has no Today button") }
        todayButton.tap()
        try waitUntil("Calendar did not navigate to the current date") {
            try selectedDate() == Day.today
        }
    }

    /// Select an unselected date in the day strip and verify navigation.
    func selectAnotherVisibleDay() throws -> Day {
        let before = try selectedDate()
        let weekday = "^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday), [A-Za-z]+ [0-9]+$"
        let candidate = app.buttons
            .matching(NSPredicate(format: "label MATCHES %@ OR identifier MATCHES %@", weekday, weekday))
            .allElementsBoundByIndex.first(where: \.isVisible)
        guard let candidate else {
            throw PageError("No alternate date is visible in Calendar's day strip")
        }
        candidate.tap()
        try waitUntil("Calendar date did not change") { try selectedDate() != before }
        return try selectedDate()
    }

    func tapBackToMonth() {
        backButton.tap()
    }

    func tapAddEvent() throws -> NewEvent {
        guard addButton.waitForVisible() else { throw PageError("Calendar has no Add button") }
        addButton.tap()
        return NewEvent(app: app)
    }

    func tapCalendars() throws -> CalendarsList {
        guard calendarsButton.waitForVisible() else {
            throw PageError("Calendar has no Calendars button")
        }
        calendarsButton.tap()
        return CalendarsList(app: app)
    }

    /// Identifiers of the visible events ("event-shown:<title>").
    func visibleDatesWithEvents() -> [String] {
        app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "event-shown:"))
            .allElementsBoundByIndex.map(\.identifier)
    }
}

/// The Calendars list sheet.
/// Port of the simulator-runnable parts of src/uiautomation/pages/calendar/calendars_list.py.
@MainActor
struct CalendarsList {
    let app: XCUIApplication

    var doneButton: XCUIElement { app.element("done-button") }
    var title: XCUIElement { app.staticTexts["Calendars"].firstMatch }

    var isOnCalendarsList: Bool { title.waitForVisible() }

    /// Calendar names, from cell labels that read "<name>, <details>".
    func calendarNames() -> [String] {
        let cells = app.cells.matching(
            NSPredicate(format: "identifier CONTAINS %@", "calendarlist-cell"))
        _ = cells.firstMatch.appears(timeout: 5)
        return cells.allElementsBoundByIndex
            .map { ($0.label.components(separatedBy: ",").first ?? "").trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
    }

    @discardableResult
    func tapDone() throws -> CalendarHome {
        try waitUntil("Calendars list has no usable Done button") {
            doneButton.isVisible && doneButton.isEnabled
        }
        doneButton.tap()
        try waitUntil("Calendars list did not close") { !title.exists }
        return CalendarHome(app: app)
    }
}
