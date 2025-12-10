import SwiftUI
import MAStyle
import AppKit

struct SettingsView: View {
    @Binding var useDarkTheme: Bool
    var statusText: String
    var dataPath: String?

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            HStack {
                Text("Settings")
                    .maText(.headline)
                Spacer()
            }
            HStack {
                Text("Theme")
                    .maText(.caption)
                Toggle("", isOn: $useDarkTheme)
                    .maToggleStyle()
                    .labelsHidden()
                Spacer()
                if !statusText.isEmpty {
                    Text(statusText)
                        .maBadge(.info)
                }
            }
            if let dataPath {
                HStack(spacing: MAStyle.Spacing.xs) {
                    Text("Data path")
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                    Text(dataPath)
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                        .lineLimit(1)
                        .truncationMode(.middle)
                        .frame(maxWidth: 300, alignment: .leading)
                    Spacer()
                    Button("Reveal") {
                        NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: dataPath)])
                    }
                    .maButton(.ghost)
                    Button("Copy") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(dataPath, forType: .string)
                    }
                    .maButton(.ghost)
                }
            }
        }
        .padding(MAStyle.Spacing.md)
    }
}
