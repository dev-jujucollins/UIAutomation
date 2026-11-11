import XCTest

/// A page-object failure. Thrown errors fail the running test with this message.
struct PageError: Error, CustomStringConvertible {
    let description: String

    init(_ description: String) {
        self.description = description
    }
}

/// Random lowercase hex for test-owned names, like Python's `uuid4().hex[:length]`.
func randomToken(_ length: Int = 12) -> String {
    String(UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased().prefix(length))
}

/// Poll `condition` until it returns true, or throw `message` after `timeout` seconds.
@MainActor
func waitUntil(
    timeout: TimeInterval = 10,
    _ message: @autoclosure () -> String,
    _ condition: () throws -> Bool
) throws {
    let deadline = Date().addingTimeInterval(timeout)
    repeat {
        if try condition() { return }
        RunLoop.current.run(until: Date().addingTimeInterval(0.25))
    } while Date() < deadline
    // Built only now, so a message can report what the screen showed at the end.
    throw PageError(message())
}

extension XCUIApplication {
    /// First element of any type with this accessibility identifier or label.
    func element(_ identifier: String) -> XCUIElement {
        descendants(matching: .any).matching(identifier: identifier).firstMatch
    }
}

extension XCUIApplication {
    /// First element of any type matching an NSPredicate format string.
    func firstElement(where format: String, _ arguments: CVarArg...) -> XCUIElement {
        descendants(matching: .any)
            .matching(NSPredicate(format: format, argumentArray: arguments))
            .firstMatch
    }

    /// Swipe up until `element` is on screen and tappable. Returns whether it got there.
    @discardableResult
    func scroll(to element: XCUIElement, in container: XCUIElement? = nil, maxSwipes: Int = 5)
        -> Bool
    {
        for _ in 0..<maxSwipes where !element.isVisible {
            (container ?? self).swipeUp()
        }
        return element.isVisible
    }
}

extension XCUIElement {
    /// In the accessibility tree, on screen, and not covered: Appium's `is_displayed`.
    var isVisible: Bool { exists && isOnScreen && isHittable }

    /// Whether the element's frame is within the screen. Checked before `isHittable`,
    /// which records a test failure when asked about some off-screen elements (such as
    /// software-keyboard keys while a hardware keyboard is connected).
    var isOnScreen: Bool {
        // Read through a snapshot, which throws if the element has just gone away;
        // reading `frame` directly records a test failure instead.
        guard exists, let frame = (try? snapshot())?.frame else { return false }
        return !frame.isEmpty && ScreenBounds.frame.intersects(frame)
    }

    /// Wait for the element to exist. Unlike `waitForExistence`, which always spends about
    /// a second before its first check, this returns at once when it is already there.
    func appears(timeout: TimeInterval = 10) -> Bool {
        exists || waitForExistence(timeout: timeout)
    }

    /// Wait for the element to be on screen and tappable.
    func waitForVisible(timeout: TimeInterval = 10) -> Bool {
        guard appears(timeout: timeout) else { return false }
        return isVisible || (try? waitUntil(timeout: timeout, "") { self.isVisible }) != nil
    }
}

extension XCUIElement {
    /// The field's text, treating UIKit's placeholder-as-value as empty.
    var textValue: String {
        guard let value = value as? String, value != placeholderValue else { return "" }
        return value
    }

    /// Whether the keyboard is typing into this element. XCUITest tracks this for its own
    /// "has keyboard focus" errors but does not publish it, so it is read by name.
    var hasKeyboardFocus: Bool {
        (value(forKey: "hasKeyboardFocus") as? Bool) ?? false
    }

    /// Clear a text field and optionally type new text. XCUITest has no `clear()`.
    func replaceText(with text: String) {
        // Typing fails without focus. A tap can return before focus moves (idle waits
        // off), and Messages sometimes ignores a tap on its message field, so tap again
        // if needed; tapping a text field twice only re-places the cursor.
        for _ in 0..<3 where !hasKeyboardFocus {
            tap()
            _ = try? waitUntil(timeout: 2, "") { self.hasKeyboardFocus }
        }
        if !textValue.isEmpty {
            // A field's own clear button is exact wherever the cursor is.
            let clear = buttons["Clear text"].firstMatch
            if clear.exists { clear.tap() }
        }
        let remaining = textValue
        if !remaining.isEmpty {
            // Otherwise put the cursor at the end and delete one character at a time.
            coordinate(withNormalizedOffset: CGVector(dx: 0.95, dy: 0.9)).tap()
            typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: remaining.count))
        }
        if !text.isEmpty { typeText(text) }
    }
}

extension XCUIApplication {
    /// First on-screen element with this identifier or label, when several share it.
    func visible(_ identifier: String) -> XCUIElement? {
        descendants(matching: .any).matching(identifier: identifier)
            .allElementsBoundByIndex.first { $0.isOnScreen && $0.isHittable }
    }
}

/// The device's screen rectangle, read once from the home screen app.
@MainActor
enum ScreenBounds {
    static let frame = XCUIApplication(bundleIdentifier: "com.apple.springboard").frame
}

extension XCUIElement {
    /// Whether a switch, toggle button or segment is on. Appium reports all of these as
    /// value "1"; XCUITest reports buttons and segments through `isSelected` instead.
    var isOn: Bool { value as? String == "1" || isSelected }

    /// Tap the element, or its centre when XCUITest reports it as not hittable even though
    /// it is on screen (some sheet buttons on iOS 27).
    func tapEvenIfNotHittable() {
        if isHittable {
            tap()
        } else {
            coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        }
    }
}

extension XCUIApplication {
    /// Whether XCUITest waits for the app to go idle before and after each event.
    ///
    /// Some screens never go idle (an open context menu in Files, Maps while it animates),
    /// and XCUITest then waits a full minute at every tap. With the waits off, page objects
    /// must wait for explicit state themselves.
    ///
    /// This sets a private XCUITest option (`currentInteractionOptions`: 1 skips the wait
    /// before an event, 2 the wait after), observed on Xcode 27.2; Appium's
    /// `waitForIdleTimeout` does the same job through WebDriverAgent. If a later Xcode
    /// drops the option, this does nothing and the normal waits apply.
    func setIdleWaits(enabled: Bool) {
        let key = "currentInteractionOptions"
        guard responds(to: NSSelectorFromString(key)),
              responds(to: NSSelectorFromString("setCurrentInteractionOptions:"))
        else { return }
        setValue(enabled ? 0 : 3, forKey: key)
    }

    /// Run `body` with idle waits off, then turn them back on.
    func withoutIdleWaits<T>(_ body: () throws -> T) rethrows -> T {
        setIdleWaits(enabled: false)
        defer { setIdleWaits(enabled: true) }
        return try body()
    }
}
