import Photos
import SwiftUI
import UIKit

/// Host app for the UI tests. The tests drive Apple's system apps by bundle ID; this app
/// only does the host-side jobs a UI test cannot do itself.
///
/// Launched with `-UIAutomationImportPhoto R,G,B` it adds one solid-colour photo to the
/// Photos library (the Python suite uses `simctl addmedia` for this) and reports the
/// outcome in the "HostApp.status" label: "imported", "denied", or "failed: <reason>".
@main
struct HostApp: App {
    var body: some Scene {
        WindowGroup {
            StatusView()
        }
    }
}

private struct StatusView: View {
    @State private var status = "idle"

    var body: some View {
        Text(status)
            .accessibilityIdentifier("HostApp.status")
            .task {
                guard let request = UserDefaults.standard.string(forKey: "UIAutomationImportPhoto")
                else { return }
                status = "importing"
                status = await PhotoImporter.importSolidColor(request)
            }
    }
}

private enum PhotoImporter {
    /// Add a 64×64 PNG of the given "R,G,B" colour (0–255 each) to the photo library.
    /// The image has no EXIF data, so Photos dates it at import.
    static func importSolidColor(_ rgb: String) async -> String {
        let parts = rgb.split(separator: ",").compactMap { Double($0) }
        guard parts.count == 3 else { return "failed: expected R,G,B" }

        let status = await PHPhotoLibrary.requestAuthorization(for: .addOnly)
        guard status == .authorized || status == .limited else { return "denied" }

        let color = UIColor(
            red: parts[0] / 255, green: parts[1] / 255, blue: parts[2] / 255, alpha: 1)
        let size = CGSize(width: 64, height: 64)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let image = UIGraphicsImageRenderer(size: size, format: format).image { context in
            color.setFill()
            context.fill(CGRect(origin: .zero, size: size))
        }
        guard let data = image.pngData() else { return "failed: could not encode PNG" }

        do {
            try await PHPhotoLibrary.shared().performChanges {
                PHAssetCreationRequest.forAsset().addResource(with: .photo, data: data, options: nil)
            }
            return "imported"
        } catch {
            return "failed: \(error.localizedDescription)"
        }
    }
}
