import SwiftUI
import MAStyle
import AppKit

struct SettingsSheet: View {
    @Binding var useDarkTheme: Bool
    var statusText: String
    var dataPath: String?
    var onClose: (() -> Void)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
            HStack(spacing: MAStyle.Spacing.sm) {
                Text("Settings")
                    .maText(.headline)
                Spacer()
                Button(action: { onClose?() }) {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .bold))
                        .padding(6)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Close settings")
            }
            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
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
                    VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                        Text("Data location")
                            .maText(.caption)
                            .foregroundStyle(MAStyle.ColorToken.muted)
                        HStack(spacing: MAStyle.Spacing.xs) {
                            Text(dataPath)
                                .maText(.caption)
                                .foregroundStyle(MAStyle.ColorToken.muted)
                                .lineLimit(1)
                                .truncationMode(.middle)
                                .frame(maxWidth: .infinity, alignment: .leading)
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
            }
        }
        .padding(MAStyle.Spacing.md)
        .frame(width: 320, alignment: .topLeading)
        .background(MAStyle.ColorToken.panel)
        .cornerRadius(MAStyle.Radius.md)
        .shadow(color: .black.opacity(0.25), radius: 14, x: 0, y: 8)
        .fixedSize(horizontal: false, vertical: true)
    }
}
