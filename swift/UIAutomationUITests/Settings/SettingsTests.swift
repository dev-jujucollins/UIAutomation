import XCTest

/// Settings navigation and General > About.
/// Port of the simulator-runnable tests in tests/integration/test_settings.py; the Wi-Fi,
/// display, Airplane Mode and search cases need a physical iPhone and are not ported yet.
final class SettingsTests: SystemAppTestCase {
    override class var bundleID: String { SettingsHome.bundleID }

    private var home: SettingsHome!

    override func setUpWithError() throws {
        try super.setUpWithError()
        home = SettingsHome(app: app)
        try home.assertHomeVisuallyReady()
    }

    /// Settings launches to a visible, usable home screen. (smoke)
    func testSettingsAppLaunches() throws {
        try home.assertHomeVisuallyReady()
    }

    func testNavigateToGeneral() throws {
        let general = try home.goToGeneral()
        XCTAssertTrue(general.isOnGeneralPage)
    }

    /// General > About opens. (journey)
    func testNavigateToGeneralAbout() throws {
        let general = try home.goToGeneral()
        XCTAssertTrue(general.isOnGeneralPage)
        let about = try general.goToAbout()
        XCTAssertTrue(about.isOnAboutPage)
    }

    /// Read device identity and OS version in one visit to About.
    func testAboutDeviceInformation() throws {
        let about = try home.goToGeneral().goToAbout()

        let deviceName = try XCTUnwrap(about.deviceName(), "Device name missing")
        XCTAssertFalse(deviceName.trimmingCharacters(in: .whitespaces).isEmpty)

        let iosVersion = try XCTUnwrap(about.iosVersion(), "iOS version missing")
        XCTAssertNotNil(
            iosVersion.range(of: #"^\d+\.\d+"#, options: .regularExpression),
            "iOS version invalid: \(iosVersion)")

        let modelName = try XCTUnwrap(about.modelName(), "Model name missing")
        XCTAssertFalse(modelName.trimmingCharacters(in: .whitespaces).isEmpty)
    }

    // MARK: Diagnostics (opt-in)

    /// Key controls of this screen still match. (diagnostic, locators)
    func testLocatorHealth() throws {
        try RunOptions.requireDiagnostics()
        assertLocatorsFound([
            "General row": home.generalCell,
            "Accessibility row": home.accessibilityCell,
            "Search field": home.searchField,
        ])
    }

    /// Every control on this screen has an accessibility label. (diagnostic, accessibility)
    func testAccessibilityLabels() throws {
        try RunOptions.requireDiagnostics()
        try assertLabelled()
    }
}
