import CoreLocation
import XCTest

/// Maps search, route previews, and simulated navigation, observed on the English
/// iOS 27 simulator.
/// Port of src/uiautomation/pages/maps/maps_page.py.
@MainActor
struct MapsPage {
    nonisolated static let bundleID = "com.apple.Maps"
    /// Every Maps test runs with the simulator located at Apple Park, Cupertino.
    nonisolated static let applePark = CLLocation(latitude: 37.3349, longitude: -122.00902)
    nonisolated static let networkTimeout: TimeInterval = 45

    enum Mode: String {
        case drive = "DriveButton"
        case walk = "WalkButton"
    }

    let app: XCUIApplication

    static let search = "MapsSearchTextField"
    static let home = "HomeView"
    static let place = "PlaceHeaderView"
    static let directions = "ActionRowItemTypeDirections"
    static let route = "IOSRoutePlanningOverview"
    // iOS 27.2 replaced CardButtonTypeClose with "close" (place) and "CloseButton" (directions).
    static let cardCloseNames = ["CardButtonTypeClose", "close", "CloseButton"]
    static let recenter = "UserLocationButton"
    static let navTray = "NavTray"

    private var cardClose: XCUIElement? {
        app.buttons.matching(
            NSPredicate(
                format: "identifier IN %@ OR label IN %@", Self.cardCloseNames, Self.cardCloseNames)
        ).allElementsBoundByIndex.first(where: \.isVisible)
    }

    private var applePark: XCUIElement? {
        app.otherElements.matching(
            NSPredicate(format: "label BEGINSWITH %@", "Apple Park Visitor Center")
        ).allElementsBoundByIndex.first(where: \.isVisible)
    }

    /// Dismiss only recognized Maps prompts; leave unexpected alerts to fail.
    func dismissKnownOnboarding(_ permission: Permission = .deny) throws -> Bool {
        if try SystemPrompts.answer(in: app, context: "Maps", permission: permission) {
            return true
        }
        let sheets: [(heading: String, buttons: [String])] = [
            ("Get Notified When Friends Share Their ETAs", ["Dismiss", "Not Now"]),
            ("EnrichmentWarmingSheetGraphic_Light", ["Continue"]),
            ("Choose Your Route Options", ["xmark.circle.fill"]),
        ]
        for sheet in sheets where app.visible(sheet.heading) != nil {
            for button in sheet.buttons {
                if let control = app.visible(button) {
                    control.tap()
                    return true
                }
            }
            throw PageError("Known Maps sheet has no dismiss control: \(sheet.heading)")
        }
        return false
    }

    /// Wait through known onboarding and asynchronous service responses for a control.
    @discardableResult
    func readyControl(
        _ what: String, permission: Permission = .deny, _ find: () -> XCUIElement?
    ) throws -> XCUIElement {
        var found: XCUIElement?
        try waitUntil(timeout: Self.networkTimeout, "Maps never showed \(what)") {
            if try dismissKnownOnboarding(permission) { return false }
            found = find()
            return found != nil
        }
        return found!
    }

    @discardableResult
    func readyControl(_ identifier: String, permission: Permission = .deny) throws -> XCUIElement {
        try readyControl(identifier, permission: permission) { app.visible(identifier) }
    }

    /// Require a home card and usable search field.
    func waitUntilReady(_ permission: Permission = .deny) throws {
        try readyControl(Self.home, permission: permission)
        try readyControl(Self.search, permission: permission)
    }

    /// Center the map on the simulated location and require nearby Apple Park.
    func recenterAtApplePark() throws {
        try readyControl(Self.recenter, permission: .allow).tap()
        try readyControl("My Location", permission: .allow)
        try readyControl("Apple Park Visitor Center", permission: .allow) { applePark }
    }

    /// The search query, treating the placeholder as empty.
    var query: String { app.element(Self.search).textValue }

    /// Replace the query without selecting a suggestion or submitting it.
    func editSearch(_ query: String) throws {
        let field = try readyControl(Self.search)
        field.replaceText(with: query)
        try waitUntil("Maps search shows '\(self.query)', not '\(query)'") { self.query == query }
    }

    /// Submit a specific query and require its expected place card.
    func searchPlace(_ query: String, expectedName: String) throws {
        try editSearch(query)
        // Return submits the search, with or without the software keyboard on screen.
        app.element(Self.search).typeText("\n")
        var openedSuggestion = false
        try readyControl("the \(expectedName) place card") {
            if let place = app.visible(Self.place) { return place }
            // A list of matches instead of a card: open the row for this place, once.
            if !openedSuggestion,
               let row = app.buttons.matching(identifier: "MultiTextView").allElementsBoundByIndex
                .first(where: { suggestion in
                    suggestion.isVisible && suggestion.label.hasPrefix("\(expectedName),")
                        && !suggestion.label.contains("Search Nearby")
                })
            {
                row.tap()
                openedSuggestion = true
            }
            return nil
        }
        try assertPlace(expectedName)
    }

    /// Verify place identity and an available Directions action.
    func assertPlace(_ expectedName: String) throws {
        let label = try readyControl(Self.place).label
        let name = label.components(separatedBy: ",").first ?? ""
        guard name == expectedName else { throw PageError("Maps opened the wrong place: \(label)") }
        try readyControl(Self.directions)
    }

    /// Open route planning from the current place card.
    func openDirections() throws {
        try readyControl(Self.directions).tap()
        try readyControl(Self.route)
    }

    /// Open a driving preview with explicit coordinates via the Maps URL handler.
    func previewRoute(from origin: CLLocationCoordinate2D, to destination: CLLocationCoordinate2D)
        throws
    {
        precondition(
            CLLocationCoordinate2DIsValid(origin) && CLLocationCoordinate2DIsValid(destination),
            "Route coordinates out of range")
        var components = URLComponents(string: "http://maps.apple.com/")!
        components.queryItems = [
            URLQueryItem(name: "saddr", value: "\(origin.latitude),\(origin.longitude)"),
            URLQueryItem(name: "daddr", value: "\(destination.latitude),\(destination.longitude)"),
            URLQueryItem(name: "dirflg", value: "d"),
        ]
        app.open(components.url!)
        try readyControl(Self.route)
        _ = try routeSummary()
    }

    /// Ordered endpoint labels, excluding the Add Stop affordance.
    func waypoints() -> [String] {
        app.descendants(matching: .any).matching(identifier: "WaypointNameText")
            .allElementsBoundByIndex
            .filter(\.isVisible).map(\.label).filter { $0 != "Add Stop" }
    }

    /// Require positive duration and distance without fixing live ETA values.
    static func validSummary(_ label: String) -> Bool {
        func firstNumber(_ pattern: String) -> Double? {
            guard let regex = try? NSRegularExpression(pattern: pattern),
                  let match = regex.firstMatch(
                    in: label, range: NSRange(label.startIndex..., in: label)),
                  let range = Range(match.range(at: 1), in: label)
            else { return nil }
            return Double(label[range].replacingOccurrences(of: ",", with: ""))
        }
        let duration = firstNumber(#"(\d+(?:\.\d+)?)\s*(?:min|hr|hour|day)\b"#) ?? 0
        let distance = firstNumber(#"(\d+(?:[.,]\d+)?)\s*(?:mi|km|ft|m)\b"#) ?? 0
        return duration > 0 && distance > 0
    }

    /// Wait for visible route duration and distance; errors cannot pass as routes.
    func routeSummary() throws -> String {
        let cells = app.otherElements.matching(identifier: "RoutePlanningCell")
        let named = NSPredicate(format: "identifier BEGINSWITH %@", "TitleLabel-SubtitleLabel")
        var summary = ""
        try waitUntil(timeout: Self.networkTimeout, "Maps never showed a valid route summary") {
            _ = try dismissKnownOnboarding()
            // Current iOS exposes the summary as text; older releases as a container.
            let candidates =
                cells.children(matching: .staticText).matching(named).allElementsBoundByIndex
                + cells.children(matching: .other).matching(named).allElementsBoundByIndex
            for candidate in candidates where candidate.isVisible {
                if Self.validSummary(candidate.label) {
                    summary = candidate.label
                    return true
                }
            }
            return false
        }
        return summary
    }

    /// Start simulated guidance and require a maneuver and destination tray.
    func startNavigation(to destination: String) throws -> String {
        try readyControl("StepsLabel-StepsLabel").tap()
        try readyControl(Self.navTray)
        let tray = try readyControl("DefaultLabel").label
        guard tray.hasPrefix("To \(destination),") else {
            throw PageError("Maps is navigating somewhere else: \(tray)")
        }
        let maneuver = try readyControl("NavManeuverSignView").label
        guard !maneuver.trimmingCharacters(in: .whitespaces).isEmpty else {
            throw PageError("Maps guidance shows no maneuver")
        }
        return maneuver
    }

    /// End a test-started route through Maps' own End Route control.
    func endNavigation() throws {
        guard app.visible(Self.navTray) != nil else { return }
        try readyControl("Card grabber").tap()
        try readyControl("End Route") {
            let button = app.buttons.matching(NSPredicate(format: "label == %@", "End Route"))
                .firstMatch
            return button.isVisible ? button : nil
        }.tap()
        try readyControl(Self.place)
    }

    /// Switch route mode and require its selected state and valid route data.
    @discardableResult
    func selectMode(_ mode: Mode) throws -> String {
        try readyControl(mode.rawValue).tap()
        let button = app.element(mode.rawValue)
        try waitUntil("Maps never selected \(mode)") { button.isOn }
        return try routeSummary()
    }

    /// Dismiss owned route/place/search sheets with a bounded cleanup loop.
    func closeToHome() throws {
        for _ in 0..<6 {
            if try dismissKnownOnboarding() { continue }
            if let close = cardClose ?? app.visible("Close") {
                close.tap()
                continue
            }
            if app.visible(Self.home) != nil, app.visible(Self.search) != nil {
                try waitUntilReady()
                return
            }
            throw PageError("Maps cleanup found no known sheet or home controls")
        }
        throw PageError("Maps cleanup exceeded six sheet dismissals")
    }
}
