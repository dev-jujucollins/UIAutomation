import XCTest

/// Settings home screen. Rows carry com.apple.settings.* accessibility identifiers.
/// Port of the simulator-runnable parts of src/uiautomation/pages/settings/settings_home.py.
@MainActor
struct SettingsHome {
    nonisolated static let bundleID = "com.apple.Preferences"

    /// Rows at the top of Settings. At the largest Dynamic Type sizes the Apple Account
    /// row alone fills the screen, so one visible anchor is enough.
    nonisolated static let initialScreenAnchors = [
        "com.apple.settings.primaryAppleAccount",
        "com.apple.settings.airplaneMode",
        "com.apple.settings.wifi",
        "com.apple.settings.bluetooth",
        "com.apple.settings.general",
        "com.apple.settings.accessibility",
    ]

    let app: XCUIApplication

    var generalCell: XCUIElement { app.element("com.apple.settings.general") }
    var wifiCell: XCUIElement { app.element("com.apple.settings.wifi") }
    var accessibilityCell: XCUIElement { app.element("com.apple.settings.accessibility") }
    // The search field sits in the bottom toolbar.
    var searchField: XCUIElement { app.searchFields["Search"].firstMatch }

    var isOnSettingsHome: Bool { generalCell.isVisible || wifiCell.isVisible }

    /// Reasons the initial screen is not usable yet. Empty means ready.
    func homeReadinessFailures() -> [String] {
        guard app.state == .runningForeground else {
            return ["Settings is not running in the foreground"]
        }
        if app.alerts.firstMatch.exists {
            return ["visible alert blocks Settings home"]
        }
        // Settings uses a collection view on current iOS and a table on older releases.
        let lists = [app.collectionViews.firstMatch, app.tables.firstMatch].filter(\.exists)
        guard !lists.isEmpty else {
            return ["Settings list is not visible"]
        }
        let anchors = NSPredicate(format: "identifier IN %@", Self.initialScreenAnchors)
        let anchorVisible = lists.contains { list in
            list.descendants(matching: .any).matching(anchors).allElementsBoundByIndex
                .contains(where: \.isVisible)
        }
        return anchorVisible ? [] : ["no expected initial Settings row is visible"]
    }

    /// Wait within one timeout budget for a visible, unblocked Settings home.
    func assertHomeVisuallyReady(timeout: TimeInterval = 10) throws {
        var failures: [String] = []
        do {
            try waitUntil(timeout: timeout, "") {
                failures = homeReadinessFailures()
                return failures.isEmpty
            }
        } catch {
            throw PageError("Settings app not visually ready: " + failures.joined(separator: "; "))
        }
    }

    func goToGeneral() throws -> GeneralSettings {
        guard app.scroll(to: generalCell) else {
            throw PageError("General row not found in Settings")
        }
        generalCell.tap()
        return GeneralSettings(app: app)
    }
}
