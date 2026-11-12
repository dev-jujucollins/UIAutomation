import XCTest

/// Photos library and viewer on the simulator's sample photos, plus one imported photo.
/// Port of tests/integration/test_photos.py.
final class PhotosTests: SystemAppTestCase {
    override class var bundleID: String { PhotosLibrary.bundleID }

    private var library: PhotosLibrary!

    override func setUpWithError() throws {
        try super.setUpWithError()
        library = PhotosLibrary(app: app)
        try library.waitUntilReady()
    }

    /// "Photo, October 09, 2009, 2:09 PM" -> the viewer's "October 9, 2009".
    static func viewerDate(fromGridLabel label: String) throws -> String {
        let parts = label.components(separatedBy: ", ")
        let parser = DateFormatter()
        parser.locale = Locale(identifier: "en_US_POSIX")
        parser.dateFormat = "MMMM dd, yyyy"
        guard parts.count >= 3, let date = parser.date(from: "\(parts[1]), \(parts[2])") else {
            throw PageError("Unexpected photo label: \(label)")
        }
        parser.dateFormat = "MMMM d, yyyy"
        return parser.string(from: date)
    }

    /// The open grid does not pick up imports; a relaunch reloads the library.
    private func relaunchedLibrary() throws -> PhotosLibrary {
        relaunch()
        try library.waitUntilReady()
        return library
    }

    /// Photos reaches its Library grid past What's New and permission prompts. (smoke)
    func testPhotosLibraryIsReady() throws {
        XCTAssertEqual(try library.photoCount(), library.photoLabels().count)
    }

    /// A sample photo opens in the viewer with its capture date; Back returns. (journey)
    func testOpenPhotoShowsItsDateAndReturns() throws {
        // Three separators means the label has a year, so the photo is not from this year.
        let dated = library.photoLabels().filter { $0.components(separatedBy: ", ").count >= 4 }
        let first = try XCTUnwrap(dated.first, "Expected the simulator's sample photos")
        let viewer = try library.openPhoto(first)
        XCTAssertTrue(viewer.showsText(try Self.viewerDate(fromGridLabel: first)))
        try viewer.goBack()
    }

    /// An imported photo appears, toggles Favorite, and leaves the library when deleted.
    ///
    /// Deleted photos stay in Recently Deleted for 30 days; that album needs a passcode,
    /// so tests cannot empty it. Run this only on a disposable simulator.
    /// (lifecycle, regression)
    func testImportedPhotoFavoriteAndDelete() throws {
        try RunOptions.requireLifecycle()
        let beforeLabels = Set(library.photoLabels())
        let before = try library.photoCount()

        // Registered before importing, so a failure at any later step still cleans up.
        // Only photos absent before the import are this test's; delete those.
        addCleanup {
            var library = try self.relaunchedLibrary()
            for label in library.photoLabels() where !beforeLabels.contains(label) {
                try library.openPhoto(label).delete()
                library = try self.relaunchedLibrary()
            }
        }

        let seed = withUnsafeBytes(of: UUID().uuid) { Array($0.prefix(3)) }
        try HostAppHelper.importPhoto(red: seed[0], green: seed[1], blue: seed[2])
        try relaunchedLibrary().waitForCount(before + 1)
        let added = library.photoLabels().filter { !beforeLabels.contains($0) }
        XCTAssertEqual(added.count, 1, "Expected exactly one new photo, found \(added)")
        let owned = try XCTUnwrap(added.first)

        let viewer = try library.openPhoto(owned)
        XCTAssertTrue(viewer.showsText("Today"))
        try viewer.setFavorite(true)
        try viewer.setFavorite(false)
        try viewer.delete()
        try viewer.goBack()

        try relaunchedLibrary().waitForCount(before)
        XCTAssertFalse(library.photoLabels().contains(owned))
    }

    // MARK: Diagnostics (opt-in)

    /// Key controls of this screen still match. (diagnostic, locators)
    func testLocatorHealth() throws {
        try RunOptions.requireDiagnostics()
        assertLocatorsFound([
            "Library view": library.libraryNav,
            "Library tab": library.libraryTab,
            "Collections tab": library.collectionsTab,
            "Search tab": library.searchTab,
        ])
    }

    /// Every control on this screen has an accessibility label. (diagnostic, accessibility)
    func testAccessibilityLabels() throws {
        try RunOptions.requireDiagnostics()
        try assertLabelled()
    }
}
