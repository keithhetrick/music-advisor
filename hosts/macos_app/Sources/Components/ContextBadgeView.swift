import SwiftUI
import AppKit
import MAStyle

struct ContextBadgeView: View {
    var title: String
    var subtitle: String
    var lastUpdated: Date?
    var path: String?
    var onOpen: (() -> Void)?

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            HStack(spacing: MAStyle.Spacing.sm) {
                Text(title)
                    .maBadge(.info)
                if !subtitle.isEmpty {
                    Text(subtitle)
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                }
                if let path {
                    Button {
                        if let onOpen { onOpen() }
                        else {
                            NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: path)])
                        }
                    } label: {
                        Label("View context", systemImage: "doc.text.magnifyingglass")
                    }
                    .maButton(.ghost)
                    .buttonStyle(.plain)
                    .accessibilityLabel("View full context file")
                }
                Spacer()
            }
            if let lastUpdated,
               let relative = Self.relativeDateFormatter.string(for: lastUpdated) {
                HStack(spacing: MAStyle.Spacing.xs) {
                    Image(systemName: "clock.arrow.circlepath")
                        .foregroundStyle(MAStyle.ColorToken.muted)
                    Text("Updated \(relative)")
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                    Spacer()
                }
            }
        }
    }

    private static let relativeDateFormatter: RelativeDateTimeFormatter = {
        let fmt = RelativeDateTimeFormatter()
        fmt.unitsStyle = .abbreviated
        return fmt
    }()
}
