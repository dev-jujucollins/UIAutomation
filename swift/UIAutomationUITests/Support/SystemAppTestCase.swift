import XCTest

/// Base class for tests that drive one of Apple's system apps by bundle ID.
///
/// Each test relaunches the app, terminates it afterwards, and attaches the app's
/// accessibility hierarchy and a screenshot to any failure.
@MainActor
class SystemAppTestCase: XCTestCase {
    /// Bundle ID of the app under test; subclasses override.
    class var bundleID: String { fatalError("Subclasses must override bundleID") }

    private(set) var app: XCUIApplication!
    private var cleanups: [() throws -> Void] = []
    private var isAttachingHierarchy = false

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication(bundleIdentifier: Self.bundleID)
        try prepareForLaunch()
        // launch() terminates a running instance first, so every test starts cold.
        app.launch()
    }

    /// Device or permission setup that must happen before the app starts.
    func prepareForLaunch() throws {}

    override func tearDownWithError() throws {
        defer {
            cleanups.removeAll()
            app?.terminate()
        }
        // Newest first, like pytest finalizers. Every cleanup runs; the first error is kept.
        var firstError: Error?
        for cleanup in cleanups.reversed() {
            do { try cleanup() } catch { firstError = firstError ?? error }
        }
        if let firstError { throw firstError }
    }

    /// Register work that must run after the test even if it fails.
    /// Register before creating the state it cleans up.
    func addCleanup(_ cleanup: @escaping () throws -> Void) {
        cleanups.append(cleanup)
    }

    /// Restart the app so the next check reads persisted data, not the current screen.
    func relaunch() {
        app.launch()
    }

    // MARK: Diagnostics

    /// Fail with every key control that no longer matches, not just the first, so renamed
    /// controls show up in one pass before they break tests.
    func assertLocatorsFound(
        _ elements: KeyValuePairs<String, XCUIElement>,
        file: StaticString = #filePath, line: UInt = #line
    ) {
        let missing = elements.filter { !$0.value.exists }.map { "\($0.key): \($0.value)" }
        XCTAssertTrue(
            missing.isEmpty, "Locators matched nothing:\n  " + missing.joined(separator: "\n  "),
            file: file, line: line)
    }

    /// Elements on the current screen that VoiceOver cannot name, from XCUITest's own
    /// accessibility audit (the Python suite queries for unlabelled controls instead).
    func unlabeledControls() throws -> [String] {
        var found: [String] = []
        try app.performAccessibilityAudit(for: .sufficientElementDescription) { issue in
            let element = issue.element.map { ": \($0)" } ?? ""
            found.append(issue.compactDescription + element)
            return true  // Collected here, so the audit itself doesn't fail the test.
        }
        return found
    }

    /// Fail with every control on the current screen that has no accessibility label.
    func assertLabelled(file: StaticString = #filePath, line: UInt = #line) throws {
        let unlabeled = try unlabeledControls()
        XCTAssertTrue(
            unlabeled.isEmpty,
            "Controls without an accessibility label:\n  " + unlabeled.joined(separator: "\n  "),
            file: file, line: line)
    }

    override func record(_ issue: XCTIssue) {
        if let app, !isAttachingHierarchy {
            isAttachingHierarchy = true
            let attachment = XCTAttachment(string: app.debugDescription)
            attachment.name = "Accessibility hierarchy"
            attachment.lifetime = .keepAlways
            add(attachment)
            // Xcode keeps a screen recording of a failed test but no still image; the
            // HTML report embeds this one. The name is matched in utils/xcresult.py.
            let screenshot = XCTAttachment(
                screenshot: XCUIScreen.main.screenshot(), quality: .medium)
            screenshot.name = "Failure screenshot"
            screenshot.lifetime = .keepAlways
            add(screenshot)
            isAttachingHierarchy = false
        }
        super.record(issue)
    }
}
