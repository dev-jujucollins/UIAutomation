import XCTest

/// Opt-in switches, read from the test runner's environment.
///
/// From the command line, prefix a variable with TEST_RUNNER_ so xcodebuild passes it on:
///     TEST_RUNNER_UIAUTOMATION_RUN_LIFECYCLE=1 xcodebuild test ...
/// These replace the Python suite's --run-lifecycle, --run-maps-navigation and
/// --run-diagnostics options.
enum RunOptions {
    static let lifecycle = "UIAUTOMATION_RUN_LIFECYCLE"
    static let mapsNavigation = "UIAUTOMATION_RUN_MAPS_NAVIGATION"
    static let diagnostics = "UIAUTOMATION_RUN_DIAGNOSTICS"

    static func isEnabled(_ name: String) -> Bool {
        let value = ProcessInfo.processInfo.environment[name]?.lowercased() ?? ""
        return ["1", "true", "yes"].contains(value)
    }

    static var isSimulator: Bool {
        #if targetEnvironment(simulator)
        return true
        #else
        return false
        #endif
    }

    /// Skip unless the run opted in to tests that save and delete their own app data.
    static func requireLifecycle() throws {
        try XCTSkipUnless(isEnabled(lifecycle), "Owned-data tests require \(lifecycle)=1")
        try XCTSkipUnless(isSimulator, "Owned-data lifecycle tests require a simulator")
    }

    /// Skip unless the run opted in to starting Maps turn-by-turn guidance.
    static func requireMapsNavigation() throws {
        try XCTSkipUnless(
            isEnabled(mapsNavigation), "Maps navigation test requires \(mapsNavigation)=1")
        try XCTSkipUnless(isSimulator, "Maps navigation test requires a simulator")
    }

    /// Skip unless the run opted in to environment-dependent diagnostics.
    static func requireDiagnostics() throws {
        try XCTSkipUnless(isEnabled(diagnostics), "Diagnostics require \(diagnostics)=1")
    }

    static func requireSimulator(_ reason: String) throws {
        try XCTSkipUnless(isSimulator, reason)
    }
}
