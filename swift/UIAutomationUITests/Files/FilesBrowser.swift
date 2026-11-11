import XCTest

/// Files app locations and folders, observed on the English iOS 27.2 simulator.
///
/// Folder cells are named "<name>, Folder". Deleting moves a folder to Recently Deleted,
/// which is not passcode-locked, so tests can remove their folders completely.
/// Port of src/uiautomation/pages/files/files_page.py.
@MainActor
struct FilesBrowser {
    nonisolated static let bundleID = "com.apple.DocumentsApp"
    nonisolated static let onMyIPhone = "On My iPhone"
    nonisolated static let recentlyDeleted = "Recently Deleted"
    nonisolated static let launchTimeout: TimeInterval = 30

    let app: XCUIApplication

    static let navigationBarID = "FullDocumentManagerViewControllerNavigationBar"
    var navigationBar: XCUIElement { app.element(Self.navigationBarID) }
    var browseTab: XCUIElement { app.element("Browse") }
    var recentsTab: XCUIElement { app.element("Recents") }
    var searchField: XCUIElement { app.searchFields.firstMatch }
    var moreButton: XCUIElement { app.element("TopOverflowBarButtonItem") }
    var newFolder: XCUIElement { app.element("New Folder") }
    var renameField: XCUIElement { app.element("DOC.inlineRenameField") }

    /// Require the document browser and its tabs.
    func waitUntilReady() throws {
        try waitUntil(timeout: Self.launchTimeout, "Files browser not ready") {
            if try SystemPrompts.answer(in: app, context: "Files") { return false }
            return app.visible(Self.navigationBarID) != nil && app.visible("Browse") != nil
        }
    }

    static func locationItemID(_ name: String) -> String { "DOC.sidebar.item.\(name)" }

    func folder(_ name: String) -> XCUIElement { app.element("\(name), Folder") }

    /// Open a Browse location such as On My iPhone or Recently Deleted.
    /// Browse reopens the last location; tapping it again shows the locations list.
    func openLocation(_ name: String) throws {
        // An open location is a "DOC.browsingRoot Source: <provider>, Title: <name>"
        // container with its name in the navigation bar. The name alone is not enough:
        // the same text sits in the locations list.
        let root = app.otherElements.matching(
            NSPredicate(
                format: "identifier BEGINSWITH %@ AND identifier ENDSWITH %@",
                "DOC.browsingRoot", "Title: \(name)")
        ).firstMatch
        let title = navigationBar.staticTexts[name].firstMatch
        var tappedBrowse = false
        try waitUntil("Files location '\(name)' did not open") {
            if root.exists, title.exists { return true }
            if let item = app.visible(Self.locationItemID(name)) {
                item.tap()
                return false
            }
            // Tap Browse on every other poll so the list has time to appear.
            if !tappedBrowse, let browse = app.visible("Browse") {
                browse.tap()
                tappedBrowse = true
            } else {
                tappedBrowse = false
            }
            return false
        }
    }

    func hasFolder(_ name: String) -> Bool { folder(name).exists }

    func waitForFolder(_ name: String, present: Bool = true, timeout: TimeInterval = 10) throws {
        try waitUntil(timeout: timeout, "Folder '\(name)' never became \(present ? "present" : "absent")") {
            hasFolder(name) == present
        }
    }

    private func setInlineName(_ name: String) throws {
        // Cells are named "<name>, Folder"; a comma would make that ambiguous.
        precondition(!name.contains(","), "Folder names used by tests must not contain commas")
        guard renameField.waitForVisible() else { throw PageError("Files rename field missing") }
        // Return commits the name. (The keyboard's Done key is off screen whenever the
        // simulator has a hardware keyboard connected.)
        renameField.replaceText(with: name + "\n")
        try waitForFolder(name)
    }

    private func tapWhenVisible(_ element: XCUIElement, _ what: String) throws {
        guard element.waitForVisible() else { throw PageError("Files: \(what) not available") }
        element.tap()
    }

    /// Create a folder in the current location (More → New Folder) and name it.
    func createFolder(_ name: String) throws {
        try tapWhenVisible(moreButton, "More button")
        try tapWhenVisible(newFolder, "New Folder")
        try setInlineName(name)
    }

    /// Long-press a folder and choose a context-menu action.
    private func menu(_ name: String, action: String) throws {
        // Files never reports itself idle while a context menu is open, which would cost
        // a minute after the press and another before the tap. Without those waits, this
        // has to wait for the menu itself.
        try app.withoutIdleWaits {
            folder(name).press(forDuration: 1.0)
            let item = app.buttons[action].firstMatch
            guard item.waitForVisible() else {
                throw PageError("Files: \(action) menu action not available")
            }
            // The menu springs open; a tap sent while it is still moving misses.
            var lastFrame = CGRect.null
            try waitUntil("Files context menu never settled") {
                let frame = item.frame
                defer { lastFrame = frame }
                return frame == lastFrame
            }
            item.tap()
            // The folder's cell leaves the tree while the menu is up, so later checks
            // mean something only once the menu has closed.
            try waitUntil("Files context menu did not close after \(action)") { !item.exists }
        }
    }

    func renameFolder(_ old: String, to new: String) throws {
        try menu(old, action: "Rename")
        try setInlineName(new)
        try waitForFolder(old, present: false)
    }

    /// Move a folder to Recently Deleted; Files does not confirm.
    func deleteFolder(_ name: String) throws {
        try menu(name, action: "Delete")
        try waitForFolder(name, present: false)
    }

    /// Permanently delete a folder from Recently Deleted (the current location).
    /// The confirmation names the item; it is confirmed only when it names this folder.
    func purgeFolder(_ name: String) throws {
        try menu(name, action: "Delete Now")
        let alert = app.alerts.firstMatch
        guard alert.appears(timeout: 10) else {
            throw PageError("Files did not ask to confirm deleting '\(name)'")
        }
        guard alert.label == "Are you sure you want to delete “\(name)”?" else {
            throw PageError("Unexpected Files delete confirmation: \(alert.label)")
        }
        alert.buttons["Delete"].firstMatch.tap()
        try waitForFolder(name, present: false)
    }
}
