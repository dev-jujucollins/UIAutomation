import XCTest

/// Settings > General.
/// Port of the simulator-runnable parts of src/uiautomation/pages/settings/general_settings.py.
@MainActor
struct GeneralSettings {
    let app: XCUIApplication

    var aboutCell: XCUIElement { app.element("About") }

    var isOnGeneralPage: Bool { aboutCell.waitForVisible() }

    func goToAbout() throws -> AboutPage {
        guard aboutCell.waitForVisible() else { throw PageError("About row not found in General") }
        aboutCell.tap()
        return AboutPage(app: app)
    }
}

/// Settings > General > About. Row labels read "<Field>, <Value>".
@MainActor
struct AboutPage {
    let app: XCUIApplication

    var nameCell: XCUIElement {
        app.firstElement(where: "identifier == %@ OR label BEGINSWITH %@", "NAME_CELL_ID", "Name,")
    }
    var iosVersionCell: XCUIElement {
        app.firstElement(
            where: "identifier == %@ OR label BEGINSWITH %@", "SW_VERSION_SPECIFIER", "iOS Version")
    }
    var softwareVersionCell: XCUIElement { app.element("Software Version") }
    var modelNameCell: XCUIElement {
        app.firstElement(
            where: "identifier == %@ OR label BEGINSWITH %@", "ProductModelName", "Model Name")
    }

    var isOnAboutPage: Bool { nameCell.waitForVisible() }

    /// The value part of a "<Field>, <Value>" label; the whole label if it has no comma.
    static func value(fromLabel label: String) -> String {
        guard let comma = label.firstIndex(of: ",") else { return label }
        return label[label.index(after: comma)...].trimmingCharacters(in: .whitespaces)
    }

    func deviceName() -> String? {
        guard nameCell.appears(timeout: 5) else { return nil }
        return Self.value(fromLabel: nameCell.label)
    }

    func iosVersion() -> String? {
        for cell in [iosVersionCell, softwareVersionCell] where cell.appears(timeout: 2) {
            return Self.value(fromLabel: cell.label)
        }
        return nil
    }

    func modelName() -> String? {
        guard app.scroll(to: modelNameCell) else { return nil }
        return Self.value(fromLabel: modelNameCell.label)
    }
}
