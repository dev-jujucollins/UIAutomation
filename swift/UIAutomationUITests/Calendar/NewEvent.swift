import XCTest

/// The New Event / Edit Event sheet.
/// Port of src/uiautomation/pages/calendar/new_event.py.
@MainActor
struct NewEvent {
    let app: XCUIApplication

    private func button(named names: [String]) -> XCUIElement {
        app.buttons.matching(NSPredicate(format: "identifier IN %@ OR label IN %@", names, names))
            .firstMatch
    }

    var cancelButton: XCUIElement { button(named: ["cancel-button", "Cancel"]) }
    var addDoneButton: XCUIElement { button(named: ["add-button", "done-button", "Done"]) }
    var titleField: XCUIElement {
        app.descendants(matching: .any).matching(
            NSPredicate(
                format: "(elementType == %d OR elementType == %d) AND identifier IN %@",
                XCUIElement.ElementType.textField.rawValue,
                XCUIElement.ElementType.textView.rawValue,
                ["title-field", "magic-compose-field"])
        ).firstMatch
    }
    var locationField: XCUIElement {
        let names = ["location-video-call-field", "Location or Video Call"]
        return app.firstElement(where: "identifier IN %@ OR label IN %@", names, names)
    }
    /// The sheet's title: "New" (static text) or "New Event" (navigation bar).
    var newTitle: XCUIElement {
        app.firstElement(
            where: "(elementType == %d AND label == %@) OR (elementType == %d AND identifier == %@)",
            XCUIElement.ElementType.staticText.rawValue, "New",
            XCUIElement.ElementType.navigationBar.rawValue, "New Event")
    }
    var allDaySwitch: XCUIElement {
        app.switches.matching(
            NSPredicate(format: "identifier IN %@", ["all-day-switch", "all-day-switch-cell"])
        ).firstMatch
    }
    var collapsedDateTime: XCUIElement { app.element("date-time-collapsed-button") }
    var eventTab: XCUIElement { app.buttons["Event"].firstMatch }
    var reminderTab: XCUIElement { app.buttons["Reminder"].firstMatch }

    // The sheet is titled "New" (static text) or "New Event" (navigation bar).
    private var newTitleVisible: Bool {
        app.staticTexts["New"].firstMatch.isVisible || app.navigationBars["New Event"].firstMatch.exists
    }

    var isOnNewEventPage: Bool {
        (try? waitUntil("") { newTitleVisible }) != nil
    }

    var title: String? {
        titleField.appears() ? titleField.textValue : nil
    }

    func setTitle(_ title: String) throws {
        guard titleField.waitForVisible() else { throw PageError("Calendar title field missing") }
        titleField.tap()
        titleField.replaceText(with: title)
        try waitUntil("Calendar title did not match entered text") { self.title == title }
    }

    /// The date and time rows start collapsed behind one button.
    func expandDateTime() throws {
        if collapsedDateTime.waitForVisible(timeout: 1) { collapsedDateTime.tap() }
        guard allDaySwitch.waitForVisible() else { throw PageError("All-day switch not shown") }
    }

    func isAllDayEnabled() throws -> Bool {
        try expandDateTime()
        return allDaySwitch.value as? String == "1"
    }

    func toggleAllDay() throws {
        try expandDateTime()
        let expected = allDaySwitch.value as? String == "1" ? "0" : "1"
        // The reporting switch can wrap the control that takes the tap.
        let inner = allDaySwitch.switches.firstMatch
        (inner.exists ? inner : allDaySwitch).tap()
        try waitUntil("All-day switch did not change") { allDaySwitch.value as? String == expected }
    }

    func enableAllDay() throws {
        if try !isAllDayEnabled() { try toggleAllDay() }
    }

    var isEventTabSelected: Bool {
        eventTab.appears() && eventTab.isOn
    }

    var isDoneEnabled: Bool { addDoneButton.appears() && addDoneButton.isEnabled }

    @discardableResult
    func tapDone() throws -> CalendarHome {
        addDoneButton.tap()
        try waitUntil("Calendar editor did not close") { !titleField.exists }
        return CalendarHome(app: app)
    }

    @discardableResult
    func tapCancel() throws -> CalendarHome {
        try discard()
        return CalendarHome(app: app)
    }

    /// Close this editor (or an event's detail card) without saving, confirming any
    /// "Discard Changes" prompt, until Calendar home is steadily back.
    /// Safe to call when nothing is open, so it can run as cleanup.
    func discard() throws {
        let home = CalendarHome(app: app)
        let discardChanges = app.buttons["Discard Changes"].firstMatch
        let detailTitle = app.element("event-details-title-text")
        let detailClose = app.element("cancel-button")
        var taps = 0
        var lastTapped: (key: String, poll: Int)?
        var poll = 0
        var homeChecks = 0

        try waitUntil(
            timeout: 20, "Calendar home not restored after discarding known editor/detail screens"
        ) {
            poll += 1
            if try SystemPrompts.answer(in: app, context: "Calendar") {
                homeChecks = 0
                return false
            }
            var next: (key: String, element: XCUIElement)?
            if discardChanges.isVisible {
                next = ("discard", discardChanges)
            } else if titleField.exists || newTitleVisible {
                if cancelButton.isVisible { next = ("cancel", cancelButton) }
            } else if detailTitle.isVisible, detailClose.isVisible {
                next = ("detail-close", detailClose)
            }
            if let next {
                homeChecks = 0
                // Tap each control once and let its animation finish; retry after ~2 s.
                if lastTapped?.key != next.key || poll - (lastTapped?.poll ?? 0) > 8 {
                    guard taps < 6 else {
                        throw PageError("Calendar cleanup exceeded six known dismissals")
                    }
                    taps += 1
                    lastTapped = (next.key, poll)
                    next.element.tap()
                }
                return false
            }
            let blocked = app.alerts.firstMatch.exists || app.sheets.firstMatch.exists
            let homeReady =
                !titleField.exists && !blocked && !detailTitle.isVisible
                && (home.dayViewNavBar.isVisible || home.monthViewNavBar.isVisible)
                && home.todayButton.isVisible && home.addButton.isVisible
            homeChecks = homeReady ? homeChecks + 1 : 0
            // Two checks in a row, so a sheet that is still animating away doesn't count.
            return homeChecks >= 2
        }
    }
}
