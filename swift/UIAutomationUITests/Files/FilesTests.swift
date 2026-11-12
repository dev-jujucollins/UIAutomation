import XCTest

/// Files locations, plus one owned folder created, renamed, deleted, and purged.
/// Port of tests/integration/test_files.py.
final class FilesTests: SystemAppTestCase {
    override class var bundleID: String { FilesBrowser.bundleID }

    private var files: FilesBrowser!

    override func setUpWithError() throws {
        try super.setUpWithError()
        files = FilesBrowser(app: app)
        try files.waitUntilReady()
    }

    /// Restart Files so checks read the file system, not the current screen.
    private func relaunched() throws -> FilesBrowser {
        relaunch()
        try files.waitUntilReady()
        return files
    }

    /// Delete and purge only these generated folder names, wherever they are.
    private func removeCompletely(_ names: [String]) throws {
        let files = try relaunched()
        try files.openLocation(FilesBrowser.onMyIPhone)
        var justDeleted: [String] = []
        for name in names where files.hasFolder(name) {
            try files.deleteFolder(name)
            justDeleted.append(name)
        }
        try files.openLocation(FilesBrowser.recentlyDeleted)
        for name in justDeleted { try waitForFolderInRecentlyDeleted(name) }
        for name in names where files.hasFolder(name) { try files.purgeFolder(name) }
    }

    /// Open Recently Deleted and wait for a folder that was just deleted.
    ///
    /// Files lists a deleted folder there late (over 30 s on a busy Mac) and an open list
    /// does not refresh, so this relaunches and looks again until the folder shows.
    private func waitForFolderInRecentlyDeleted(_ name: String, attempts: Int = 8) throws {
        try files.openLocation(FilesBrowser.recentlyDeleted)
        for _ in 1..<attempts {
            if (try? files.waitForFolder(name)) != nil { return }
            try relaunched().openLocation(FilesBrowser.recentlyDeleted)
        }
        try files.waitForFolder(name)
    }

    /// Files reaches its document browser. (smoke)
    func testFilesBrowserIsReady() throws {
        XCTAssertTrue(files.searchField.waitForVisible())
    }

    /// Both local locations open from Browse. (journey)
    func testBrowseOnMyIPhoneAndRecentlyDeleted() throws {
        try files.openLocation(FilesBrowser.onMyIPhone)
        try files.openLocation(FilesBrowser.recentlyDeleted)
    }

    /// A folder persists across relaunches, renames, and is removed completely.
    /// (lifecycle, regression)
    func testFolderCreateRenameDeletePurge() throws {
        try RunOptions.requireLifecycle()
        let token = randomToken(12)
        let original = "UIAutomation \(token)"
        let renamed = "UIAutomation \(token) renamed"
        try files.openLocation(FilesBrowser.onMyIPhone)
        XCTAssertFalse(files.hasFolder(original) || files.hasFolder(renamed))
        // Registered before creating: cleanup touches only these two generated names.
        addCleanup { try self.removeCompletely([original, renamed]) }

        try files.createFolder(original)
        try relaunched().openLocation(FilesBrowser.onMyIPhone)
        XCTAssertTrue(files.hasFolder(original), "Created folder did not survive relaunch")

        try files.renameFolder(original, to: renamed)
        try relaunched().openLocation(FilesBrowser.onMyIPhone)
        XCTAssertTrue(files.hasFolder(renamed))
        XCTAssertFalse(files.hasFolder(original))

        try files.deleteFolder(renamed)
        XCTAssertNoThrow(
            try waitForFolderInRecentlyDeleted(renamed),
            "Deleted folder missing from Recently Deleted")
        try files.purgeFolder(renamed)

        try relaunched().openLocation(FilesBrowser.onMyIPhone)
        XCTAssertFalse(files.hasFolder(renamed))
        try files.openLocation(FilesBrowser.recentlyDeleted)
        XCTAssertFalse(files.hasFolder(renamed))
    }

    // MARK: Diagnostics (opt-in)

    /// Key controls of this screen still match. (diagnostic, locators)
    func testLocatorHealth() throws {
        try RunOptions.requireDiagnostics()
        assertLocatorsFound([
            "Navigation bar": files.navigationBar,
            "Browse tab": files.browseTab,
            "Recents tab": files.recentsTab,
            "Search field": files.searchField,
        ])
    }

    /// Every control on this screen has an accessibility label. (diagnostic, accessibility)
    func testAccessibilityLabels() throws {
        try RunOptions.requireDiagnostics()
        try assertLabelled()
    }
}
