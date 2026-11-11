import XCTest

enum Permission {
    case allow, deny
}

/// Buttons for one prompt; `allow` is nil when the answer never varies.
struct PromptAnswer {
    let deny: String
    var allow: String?

    func button(for permission: Permission) -> String {
        permission == .allow ? (allow ?? deny) : deny
    }
}

/// Known iOS system prompts and the button each one is answered with.
/// Port of src/uiautomation/pages/system_prompts.py.
@MainActor
enum SystemPrompts {
    static let dontAllow = "Don’t Allow"

    private static func permissionPrompts(_ app: String) -> [String: PromptAnswer] {
        [
            "Allow “\(app)” to use your location?":
                PromptAnswer(deny: dontAllow, allow: "Allow While Using App"),
            "“\(app)” Would Like to Send You Notifications": PromptAnswer(deny: dontAllow),
            "Allow “\(app)” to access your contacts?": PromptAnswer(deny: dontAllow),
        ]
    }

    /// Keyed by visible title. iOS 27 "staged" prompts can surface over any app, so every
    /// page recognizes every app's prompts. Add new prompts here; unknown alerts fail the test.
    static let known: [String: PromptAnswer] = {
        var prompts: [String: PromptAnswer] = [
            "Allow widgets from “Maps” to use your location?":
                PromptAnswer(deny: dontAllow, allow: "Allow"),
            "Getting There Safely": PromptAnswer(deny: "OK"),
            // Reminders' own first-launch alert on a simulator without an Apple Account.
            "Enable iCloud Syncing?": PromptAnswer(deny: "Not Now"),
        ]
        for app in ["Calendar", "Maps", "Reminders", "Photos"] {
            prompts.merge(permissionPrompts(app)) { current, _ in current }
        }
        return prompts
    }()

    /// Compare titles and labels regardless of curly or straight quotes.
    static func normalize(_ text: String) -> String {
        text
            .replacingOccurrences(of: "“", with: "\"")
            .replacingOccurrences(of: "”", with: "\"")
            .replacingOccurrences(of: "‘", with: "'")
            .replacingOccurrences(of: "’", with: "'")
    }

    private static let answers = Dictionary(
        uniqueKeysWithValues: known.map { (normalize($0), $1) })

    /// Answer the first visible alert if it is a known prompt.
    ///
    /// - Parameters:
    ///   - context: App under test, used in failure messages.
    ///   - permission: Decision for prompts that offer one; others use their fixed button.
    /// - Returns: true if a prompt was answered, false if no alert is showing.
    static func answer(
        in app: XCUIApplication, context: String, permission: Permission = .deny
    ) throws -> Bool {
        // Permission alerts belong to SpringBoard; app-owned alerts belong to the app.
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        for host in [app, springboard] {
            let alert = host.alerts.firstMatch
            // One snapshot, so an alert that is animating away can't fail the test by
            // disappearing between two reads; it is checked again on the next poll.
            guard alert.exists, let snapshot = try? alert.snapshot() else { continue }
            // iOS 27 permission alerts identify themselves by service ID
            // (kTCCServiceAddressBook-staged-alert); the label is the visible title.
            let title = snapshot.label.isEmpty ? snapshot.identifier : snapshot.label
            guard let answer = answers[normalize(title)] else {
                throw PageError("Unexpected \(context) alert: \(title)")
            }
            let wanted = normalize(answer.button(for: permission))
            let labels = buttonLabels(in: snapshot)
            guard let label = labels.first(where: { normalize($0) == wanted }) else {
                throw PageError("Known \(context) prompt has no '\(wanted)' button: \(title)")
            }
            let button = alert.buttons[label].firstMatch
            guard button.exists else { return false }
            button.tap()
            return true
        }
        return false
    }

    private static func buttonLabels(in snapshot: XCUIElementSnapshot) -> [String] {
        var labels = snapshot.elementType == .button ? [snapshot.label] : []
        for child in snapshot.children { labels += buttonLabels(in: child) }
        return labels
    }
}
