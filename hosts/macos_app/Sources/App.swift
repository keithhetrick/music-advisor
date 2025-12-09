import SwiftUI
import MAStyle

@main
struct MusicAdvisorMacApp: App {
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowStyle(.titleBar)
        .onChange(of: scenePhase) { phase in
            if phase == .active {
                NSApplication.shared.activate(ignoringOtherApps: true)
                NSApplication.shared.windows.first?.makeKeyAndOrderFront(nil)
            }
        }
    }
}
