import XCTest

/// Safari on pages served from this Mac (deterministic) and on apple.com (real world).
/// Port of tests/integration/test_safari.py.
final class SafariTests: SystemAppTestCase {
    override class var bundleID: String { SafariPage.bundleID }

    private var safari: SafariPage!

    override func setUpWithError() throws {
        try super.setUpWithError()
        safari = SafariPage(app: app)
        try safari.waitUntilReady()
    }

    /// Serve the fixture pages for this test and return the site's base URL.
    private func fixtureSite() throws -> URL {
        try RunOptions.requireSimulator("A physical device cannot reach this Mac's localhost")
        let site = try FixtureSite.bundled()
        addCleanup { site.stop() }
        return site.baseURL
    }

    private var homeHeading: XCUIElement { safari.text("UIAutomation fixture page") }
    private var secondHeading: XCUIElement { safari.text("Second fixture page") }

    /// Safari reaches a usable address bar past its first-launch notices. (smoke)
    func testSafariIsReady() throws {
        XCTAssertTrue(safari.tabsButton.waitForVisible())
    }

    /// A local page loads, a link navigates, and Back returns. (journey)
    func testLoadFollowLinkAndGoBack() throws {
        try safari.open(fixtureSite(), loaded: homeHeading)
        XCTAssertEqual(safari.host, "127.0.0.1")
        try safari.tap(.link, "Go to second page")
        try safari.waitFor(secondHeading)
        try safari.goBack(loaded: homeHeading)
    }

    /// Typed text, including accents, reaches page script through a web input. (journey)
    func testFormInputReachesThePage() throws {
        try safari.open(fixtureSite(), loaded: homeHeading)
        try safari.fill("Fixture input", with: "héllo 42")
        try safari.tap(.button, "Echo")
        try safari.waitFor(safari.text("Echo: héllo 42"))
    }

    /// apple.com loads over HTTPS; the site menu reaches the iPhone section; Back returns.
    /// Uses only structure that outlives marketing copy (landmarks, menu, section links);
    /// when apple.com's structure changes, update the labels here. (network, journey)
    func testAppleComMenuToIPhoneAndBack() throws {
        let globalNav = safari.web(.other, "Global, navigation")
        let iPhoneNav = safari.web(.other, "iPhone family, navigation")

        try safari.open(URL(string: "https://www.apple.com")!, loaded: globalNav)
        XCTAssertEqual(safari.host, "apple.com")
        try safari.tap(.button, "Menu")
        try safari.tap(.button, "iPhone menu")
        try safari.tap(.link, "Explore All iPhone")
        try safari.waitFor(iPhoneNav)
        XCTAssertEqual(safari.host, "apple.com")
        try safari.goBack(loaded: globalNav)
        try waitUntil("iPhone navigation still showing after Back") { !iPhoneNav.isVisible }
        XCTAssertTrue(safari.forwardButton.isVisible)
    }

    // MARK: Diagnostics (opt-in)

    /// Key controls of Safari still match. (diagnostic, locators)
    func testLocatorHealth() throws {
        try RunOptions.requireDiagnostics()
        assertLocatorsFound(["Tabs button": safari.tabsButton])
    }

    /// Every control has an accessibility label. (diagnostic, accessibility)
    func testAccessibilityLabels() throws {
        try RunOptions.requireDiagnostics()
        // Safari reopens its last tab; load a known page so only Safari's chrome is judged.
        try safari.open(fixtureSite(), loaded: homeHeading)
        try assertLabelled()
    }

    /// The check itself works: an icon-only web button with no label is reported, alone.
    /// (diagnostic, accessibility)
    func testDetectorReportsAnUnlabeledWebButton() throws {
        try RunOptions.requireDiagnostics()
        let site = try fixtureSite()
        // Leave a labelled page as Safari's last tab, so later Safari checks don't inherit this one.
        addCleanup { try self.safari.open(site, loaded: self.homeHeading) }
        try safari.open(
            site.appendingPathComponent("unlabeled.html"),
            loaded: safari.text("Unlabeled control fixture"))
        let unlabeled = try unlabeledControls().filter { $0.contains("Button") }
        XCTAssertEqual(unlabeled.count, 1, "\(unlabeled)")
    }
}
