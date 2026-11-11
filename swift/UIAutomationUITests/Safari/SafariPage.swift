import XCTest

/// Safari browser chrome and web content, observed on the English iOS 27.2 simulator.
///
/// Web elements are exposed by their accessible names: link and heading text,
/// `aria-label` for inputs, and button text.
/// Port of src/uiautomation/pages/safari/safari_page.py.
@MainActor
struct SafariPage {
    nonisolated static let bundleID = "com.apple.mobilesafari"
    nonisolated static let launchTimeout: TimeInterval = 30
    nonisolated static let pageLoadTimeout: TimeInterval = 30

    let app: XCUIApplication

    // Address bar while showing a page, and while editing.
    var addressBar: XCUIElement { app.element("TabBarItemTitle") }
    var addressField: XCUIElement { app.element("URL") }
    var backButton: XCUIElement { app.buttons["BackButton"].firstMatch }
    var forwardButton: XCUIElement { app.buttons["ForwardButton"].firstMatch }
    var tabsButton: XCUIElement { app.element("TabOverviewButton") }

    // First-launch notices, matched by their text so a generic "Not Now" is never tapped.
    private var notices: [(text: XCUIElement, dismiss: XCUIElement)] {
        [
            (app.element("Include topics from other devices"), app.buttons["Not Now"].firstMatch),
            (
                app.textViews.matching(
                    NSPredicate(format: "label BEGINSWITH %@", "Safari search now shows")
                ).firstMatch,
                app.buttons["Continue"].firstMatch
            ),
        ]
    }

    /// Answer one first-launch notice; true when something was tapped.
    private func dismissKnownNotice() throws -> Bool {
        if try SystemPrompts.answer(in: app, context: "Safari") { return true }
        for notice in notices where notice.text.isVisible {
            guard notice.dismiss.isVisible else {
                throw PageError("Known Safari notice has no dismiss control: \(notice.text)")
            }
            notice.dismiss.tap()
            return true
        }
        return false
    }

    /// Get past first-launch notices to a usable address bar.
    func waitUntilReady() throws {
        try waitUntil(timeout: Self.launchTimeout, "Safari address bar not ready") {
            if try dismissKnownNotice() { return false }
            return addressBar.isVisible || addressField.isVisible
        }
    }

    /// Open a URL in Safari and wait for an element of the loaded page.
    ///
    /// Opened as a link, not typed: the address bar autocompletes from history, so typing
    /// `http://host/` after visiting `http://host/page.html` would load the latter.
    func open(_ url: URL, loaded: XCUIElement) throws {
        app.open(url)
        try waitFor(loaded)
    }

    /// Host shown in the address bar, without Safari's left-to-right mark.
    var host: String {
        (addressBar.value as? String ?? "")
            .trimmingCharacters(in: CharacterSet(charactersIn: "\u{200E}\u{200F} "))
    }

    /// A web element by type and exact accessible label.
    ///
    /// Text and headings are `.staticText`, links are `.link`, landmarks such as
    /// `<nav aria-label>` are `.other`, inputs are `.textField` (named by aria-label).
    func web(_ type: XCUIElement.ElementType, _ label: String) -> XCUIElement {
        app.descendants(matching: type)
            .matching(NSPredicate(format: "label == %@", label))
            .firstMatch
    }

    func text(_ label: String) -> XCUIElement { web(.staticText, label) }

    func waitFor(_ element: XCUIElement) throws {
        guard element.waitForVisible(timeout: Self.pageLoadTimeout) else {
            throw PageError("Safari never showed \(element)")
        }
    }

    /// Tap a web link, button, or other element by its accessible label.
    func tap(_ type: XCUIElement.ElementType, _ label: String) throws {
        let element = web(type, label)
        try waitFor(element)
        element.tap()
    }

    /// Type into a web input identified by its accessible label (aria-label).
    func fill(_ fieldLabel: String, with value: String) throws {
        let field = web(.textField, fieldLabel)
        try waitFor(field)
        field.tap()
        field.replaceText(with: value)
    }

    /// Use Safari's Back button and wait for an element of the previous page.
    func goBack(loaded: XCUIElement) throws {
        backButton.tap()
        try waitFor(loaded)
    }
}
