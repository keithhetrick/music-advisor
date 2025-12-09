import Foundation
import AppKit
import UniformTypeIdentifiers

/// Lightweight services container to avoid stuffing helpers into ContentView.
struct AppServices {
    let filePicker: FilePickerService
    let historyLoader: HistoryLoaderService

    init(filePicker: FilePickerService = .init(),
         historyLoader: HistoryLoaderService = .init()) {
        self.filePicker = filePicker
        self.historyLoader = historyLoader
    }
}

struct FilePickerService {
    func pickFile(allowedTypes: [UTType] = [.audio, .aiff, .wav, .mp3]) -> URL? {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = allowedTypes
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.canCreateDirectories = false
        return panel.runModal() == .OK ? panel.url : nil
    }
    
    func pickDirectory() -> URL? {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.canCreateDirectories = true
        return panel.runModal() == .OK ? panel.url : nil
    }
}

struct HistoryLoaderService {
    private let historyStore = HistoryStore()

    func loadHistory() -> [SidecarItem] {
        historyStore.load()
    }

    func clearHistoryOnDisk() {
        try? SpecialActions.clearSidecarsOnDisk()
    }
}
