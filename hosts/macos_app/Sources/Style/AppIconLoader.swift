import AppKit

enum AppIconLoader {
    static func applyBundleIcon() {
        let bundle = Bundle.main
        let candidates = [
            bundle.url(forResource: "icon_512", withExtension: "png", subdirectory: "AppIcon.appiconset"),
            bundle.url(forResource: "icon_256", withExtension: "png", subdirectory: "AppIcon.appiconset"),
            bundle.url(forResource: "icon_128", withExtension: "png", subdirectory: "AppIcon.appiconset")
        ].compactMap { $0 }
        guard let url = candidates.first, let img = NSImage(contentsOf: url) else { return }
        NSApplication.shared.applicationIconImage = img
    }
}
