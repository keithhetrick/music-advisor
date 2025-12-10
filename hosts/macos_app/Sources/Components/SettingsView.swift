import SwiftUI
import MAStyle
import AppKit

struct SettingsView: View {
    @Binding var useDarkTheme: Bool
    var statusText: String
    var dataPath: String?

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            HStack {
                HStack(spacing: MAStyle.Spacing.sm) {
                    Text("Theme")
                        .maText(.caption)
                    Toggle("", isOn: $useDarkTheme)
                        .maToggleStyle()
                        .labelsHidden()
                }
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
                        .frame(maxWidth: 260, alignment: .leading)
                    Spacer()
                    Button("Reveal") {
                        NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: dataPath)])
                    }
                    .maButton(.ghost)
                    .accessibilityLabel("Reveal data folder in Finder")
                    Button("Copy") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(dataPath, forType: .string)
                    }
                    .maButton(.ghost)
                    .accessibilityLabel("Copy data path")
                }
            }
        }
        .maCard(padding: MAStyle.Spacing.sm)
    }
}
