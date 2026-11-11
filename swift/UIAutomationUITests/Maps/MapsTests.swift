import CoreLocation
import XCTest

/// Maps journeys on the simulator, including Apple Park guidance.
/// Port of tests/integration/test_maps.py.
///
/// Every test sets the simulator's location to Apple Park and forgets Maps' location
/// permission, so the prompt appears and each test answers it; both are restored afterwards.
final class MapsTests: SystemAppTestCase {
    override class var bundleID: String { MapsPage.bundleID }

    private static let origin = CLLocationCoordinate2D(latitude: 37.8029, longitude: -122.4484)
    private static let destination = CLLocationCoordinate2D(latitude: 37.8199, longitude: -122.4783)
    private static let bridgeQuery = "Golden Gate Bridge San Francisco"
    private static let bridge = "Golden Gate Bridge"

    override func prepareForLaunch() throws {
        try RunOptions.requireSimulator("Maps coverage requires a simulator")
        app.terminate()
        app.resetAuthorizationStatus(for: .location)
        XCUIDevice.shared.location = XCUILocation(location: MapsPage.applePark)
        // Registered first, so they run last: after the cleanup taps and the terminate.
        addCleanup { XCUIDevice.shared.location = nil }
        addCleanup { [app] in app?.resetAuthorizationStatus(for: .location) }
    }

    /// Answer the location prompt as asked and reach Maps home.
    private func maps(_ permission: Permission = .deny) throws -> MapsPage {
        let maps = MapsPage(app: app)
        // Maps can keep animating, and XCUITest then waits a full minute for it to go idle
        // at every tap and keystroke. Maps page objects wait for explicit state instead.
        app.setIdleWaits(enabled: false)
        try maps.waitUntilReady(permission)
        addCleanup { try maps.closeToHome() }
        return maps
    }

    // pytest parametrizes these over values; XCTest gets one method per case.

    /// Both location decisions permit manual place search and dismissal. (smoke)
    func testLaunchAndSearchWithLocationDenied() throws { try launchAndSearch(.deny) }
    func testLaunchAndSearchWithLocationAllowed() throws { try launchAndSearch(.allow) }

    private func launchAndSearch(_ permission: Permission) throws {
        let maps = try maps(permission)
        try maps.searchPlace(Self.bridgeQuery, expectedName: Self.bridge)
        try maps.closeToHome()
    }

    /// Search input can be replaced, cleared, and canceled without selecting a result.
    func testEditClearAndCancelSearchPlace() throws {
        try editClearAndCancelSearch("Golden Gate Bridge")
    }
    func testEditClearAndCancelSearchAddress() throws {
        try editClearAndCancelSearch("1 Ferry Building San Francisco")
    }

    private func editClearAndCancelSearch(_ query: String) throws {
        let maps = try maps()
        try maps.editSearch(query)
        XCTAssertEqual(maps.query, query)
        try maps.editSearch("Palace of Fine Arts")
        XCTAssertEqual(maps.query, "Palace of Fine Arts")
        try maps.editSearch("")
        XCTAssertEqual(maps.query, "")
        try maps.closeToHome()
    }

    /// Place identity and Directions entry remain usable with location denied. (journey)
    func testPlaceDirectionsRoundTrip() throws {
        let maps = try maps()
        try maps.searchPlace(Self.bridgeQuery, expectedName: Self.bridge)
        try maps.openDirections()
        XCTAssertEqual(maps.waypoints(), ["Choose an origin", Self.bridge])
        try maps.closeToHome()
    }

    /// Fixed endpoints produce driving and walking previews with valid metrics. (journey)
    func testRoutePreviewAndTravelModes() throws {
        let maps = try maps()
        try maps.previewRoute(from: Self.origin, to: Self.destination)
        let endpoints = maps.waypoints()
        XCTAssertEqual(endpoints.count, 2, "\(endpoints)")
        XCTAssertEqual(endpoints.first, "Palace of Fine Arts")
        XCTAssertTrue(endpoints.last?.hasPrefix(Self.bridge) ?? false, "\(endpoints)")
        let driving = try maps.selectMode(.drive)
        let walking = try maps.selectMode(.walk)
        XCTAssertNotEqual(walking, driving, "Walking still exposes the driving summary")
        try maps.selectMode(.drive)
        try maps.closeToHome()
    }

    /// Two complete search/dismiss cycles leave no blocking route or place card. (journey)
    func testSearchRepeatability() throws {
        let maps = try maps()
        for _ in 0..<2 {
            try maps.searchPlace(Self.bridgeQuery, expectedName: Self.bridge)
            try maps.closeToHome()
        }
    }

    /// Start driving guidance from simulated Apple Park to Golden Gate Bridge.
    /// (maps_navigation, journey)
    func testDirectionsFromAppleParkLocation() throws {
        try RunOptions.requireMapsNavigation()
        let maps = try maps(.allow)
        addCleanup { try maps.endNavigation() }
        try maps.recenterAtApplePark()
        try maps.searchPlace(Self.bridgeQuery, expectedName: Self.bridge)
        try maps.openDirections()
        XCTAssertEqual(maps.waypoints(), ["My Location", Self.bridge])
        XCTAssertTrue(MapsPage.validSummary(try maps.routeSummary()))
        XCTAssertFalse(try maps.startNavigation(to: Self.bridge).isEmpty)
    }

    // MARK: Diagnostics (opt-in)

    /// Key controls of Maps home still match. (diagnostic, locators)
    func testLocatorHealth() throws {
        try RunOptions.requireDiagnostics()
        _ = try maps()
        assertLocatorsFound([
            "Search field": app.element(MapsPage.search),
            "Home card": app.element(MapsPage.home),
            "Recenter button": app.element(MapsPage.recenter),
        ])
    }

    /// Every control on Maps home has an accessibility label. (diagnostic, accessibility)
    func testAccessibilityLabels() throws {
        try RunOptions.requireDiagnostics()
        _ = try maps()
        try assertLabelled()
    }
}
