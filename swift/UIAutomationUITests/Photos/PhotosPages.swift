import XCTest

/// The Photos Library tab's grid; each photo is an image labelled "Photo, <date>, <time>".
///
/// Labels use a narrow no-break space (U+202F) before AM/PM, and omit the year for
/// photos from the current year.
/// Port of src/uiautomation/pages/photos/photos_library.py.
@MainActor
struct PhotosLibrary {
    nonisolated static let bundleID = "com.apple.mobileslideshow"
    nonisolated static let launchTimeout: TimeInterval = 30
    nonisolated static let photoID = "PXGGridLayout-Info"

    let app: XCUIApplication

    var libraryNav: XCUIElement { app.element("PXCuratedLibraryUIView") }
    var libraryTab: XCUIElement { app.element("LibraryTab") }
    var collectionsTab: XCUIElement { app.element("CollectionsTab") }
    var searchTab: XCUIElement { app.element("SearchTab") }
    var librarySummary: XCUIElement {
        app.otherElements.matching(NSPredicate(format: "label BEGINSWITH %@", "Library, "))
            .firstMatch
    }
    var whatsNewTitle: XCUIElement { app.element("What’s New in Photos") }
    var whatsNewContinue: XCUIElement { app.buttons["Continue"].firstMatch }

    /// Get past What's New and permission prompts to a loaded library grid.
    func waitUntilReady() throws {
        try waitUntil(timeout: Self.launchTimeout, "Photos library not ready") {
            if try SystemPrompts.answer(in: app, context: "Photos") { return false }
            if whatsNewTitle.isVisible {
                if whatsNewContinue.isVisible { whatsNewContinue.tap() }
                return false
            }
            if !libraryNav.exists {
                if libraryTab.isVisible { libraryTab.tap() }
                return false
            }
            return librarySummary.exists
        }
    }

    /// Photos the library reports in its "Library, N Photos" summary.
    func photoCount() throws -> Int {
        let label = librarySummary.label
        let parts = label.split(separator: " ")
        guard parts.count == 3, parts[0] == "Library,", let count = Int(parts[1]),
              parts[2] == "Photo" || parts[2] == "Photos"
        else {
            throw PageError("Unexpected library summary: \(label)")
        }
        return count
    }

    func waitForCount(_ expected: Int) throws {
        try waitUntil("Library never reported \(expected) photos") {
            try photoCount() == expected
        }
    }

    /// Grid labels in display order (oldest first).
    func photoLabels() -> [String] {
        app.descendants(matching: .any).matching(identifier: Self.photoID)
            .allElementsBoundByIndex.map(\.label)
    }

    /// Open a photo by its exact grid label.
    func openPhoto(_ label: String) throws -> PhotoViewer {
        let photo = app.firstElement(
            where: "identifier == %@ AND label == %@", Self.photoID, label)
        guard photo.waitForVisible() else { throw PageError("No photo labelled '\(label)'") }
        photo.tap()
        let viewer = PhotoViewer(app: app)
        try viewer.waitUntilReady()
        return viewer
    }
}

/// One-up photo viewer: one photo with its date ("October 9, 2009", or "Today") and actions.
/// Port of src/uiautomation/pages/photos/photo_viewer.py.
@MainActor
struct PhotoViewer {
    let app: XCUIApplication

    var navigationBar: XCUIElement { app.element("PUOneUpView") }
    var backButton: XCUIElement { app.buttons["BackButton"].firstMatch }
    var favorite: XCUIElement { app.element("PUOneUpBarButtonItemIdentifierFavorite") }
    var deleteButton: XCUIElement { app.element("PUOneUpBarButtonItemIdentifierTrashBin") }
    // "This photo will be deleted from the library. It will be in Recently Deleted for 30 days."
    var deleteConfirm: XCUIElement { app.buttons["Delete Photo"].firstMatch }

    func waitUntilReady() throws {
        guard navigationBar.waitForVisible(), favorite.waitForVisible() else {
            throw PageError("Photo viewer not ready")
        }
    }

    /// Whether the viewer header shows this exact text (a date, a time, or "Today").
    func showsText(_ label: String) -> Bool {
        app.staticTexts.matching(NSPredicate(format: "label == %@", label)).firstMatch
            .waitForVisible(timeout: 5)
    }

    var isFavorite: Bool { favorite.isOn }

    /// Tap Favorite once if needed and wait for the control to report the new state.
    func setFavorite(_ wanted: Bool) throws {
        if isFavorite != wanted { favorite.tap() }
        try waitUntil("Favorite never became \(wanted)") { isFavorite == wanted }
    }

    /// Delete and confirm. The photo moves to Recently Deleted, which needs a passcode.
    func delete() throws {
        deleteButton.tap()
        guard deleteConfirm.waitForVisible() else { throw PageError("No Delete Photo confirmation") }
        deleteConfirm.tap()
        try waitUntil("Delete Photo confirmation did not close") { !deleteConfirm.exists }
    }

    @discardableResult
    func goBack() throws -> PhotosLibrary {
        backButton.tap()
        let library = PhotosLibrary(app: app)
        try library.waitUntilReady()
        return library
    }
}
