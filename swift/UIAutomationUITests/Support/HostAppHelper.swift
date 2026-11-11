import XCTest

/// Host-side jobs done through the test host app (see HostApp/HostApp.swift).
@MainActor
enum HostAppHelper {
    static let bundleID = "dev.uiautomation.HostApp"

    /// Add one solid-colour photo to the simulator's Photos library.
    /// Replaces the Python suite's `simctl addmedia`, which a UI test cannot run.
    static func importPhoto(red: UInt8, green: UInt8, blue: UInt8) throws {
        let host = XCUIApplication(bundleIdentifier: bundleID)
        host.launchArguments = ["-UIAutomationImportPhoto", "\(red),\(green),\(blue)"]
        // Forget any earlier answer, so the prompt appears and is allowed below. A
        // remembered "Don't Allow" would otherwise fail the import without asking.
        host.resetAuthorizationStatus(for: .photos)
        host.launch()
        defer { host.terminate() }

        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let status = host.staticTexts["HostApp.status"]
        try waitUntil(timeout: 30, "Host app never finished importing a photo") {
            // First import on a simulator: allow the host app to add to Photos.
            let alert = springboard.alerts.firstMatch
            if alert.exists {
                // "Allow “HostApp” to add photos and videos to your photo library?"
                guard alert.label.contains("add photos") else {
                    throw PageError("Unexpected alert while importing a photo: \(alert.label)")
                }
                alert.buttons["Allow"].firstMatch.tap()
                return false
            }
            guard status.exists else { return false }
            switch status.label {
            case "imported": return true
            case "idle", "importing": return false
            default: throw PageError("Host app could not import a photo: \(status.label)")
            }
        }
    }
}
