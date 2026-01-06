import SwiftUI
import MAStyle

struct InspectorPanel: View {
    enum Mode {
        case analyze
        case results
    }

    let mode: Mode
    let workingDirectory: String
    let envText: String
    let sidecarPath: String?
    let lastStatus: String
    let echoStatuses: [EchoStatus]
    let onRevealSidecar: (() -> Void)?
    let onCopySidecar: (() -> Void)?

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
            inspectorHeader
            section(title: "Working directory") {
                Text(workingDirectory.isEmpty ? "Not set" : workingDirectory)
                    .maText(.caption)
                    .foregroundStyle(workingDirectory.isEmpty ? MAStyle.ColorToken.warning : MAStyle.ColorToken.muted)
                    .lineLimit(2)
            }
            section(title: "Environment") {
                Text(envText.isEmpty ? "No extra env" : envText)
                    .font(MAStyle.Typography.bodyMono)
                    .foregroundStyle(MAStyle.ColorToken.muted)
                    .lineLimit(4)
            }
            if let sidecarPath {
                section(title: "Latest sidecar") {
                    Text(sidecarPath)
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                        .lineLimit(2)
                    HStack(spacing: MAStyle.Spacing.xs) {
                        if let onRevealSidecar {
                            Button("Reveal", action: onRevealSidecar).maButton(.ghost)
                        }
                        if let onCopySidecar {
                            Button("Copy path", action: onCopySidecar).maButton(.ghost)
                        }
                    }
                }
            }
            section(title: "Echo status") {
                if echoStatuses.isEmpty {
                    Text("No submissions yet")
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                } else {
                    ForEach(echoStatuses.prefix(3)) { status in
                        HStack {
                            Text(status.trackId).maText(.caption)
                            Spacer()
                            Text(status.status.uppercased())
                                .maText(.caption)
                                .foregroundStyle(color(for: status.status))
                        }
                    }
                    if echoStatuses.count > 3 {
                        Text("+\(echoStatuses.count - 3) more")
                            .maText(.caption)
                            .foregroundStyle(MAStyle.ColorToken.muted)
                    }
                }
            }
        }
        .padding(MAStyle.Spacing.md)
        .background(DesignTokens.Color.surface.opacity(0.95))
        .cornerRadius(DesignTokens.Radius.lg)
        .overlay(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.lg)
                .stroke(DesignTokens.Color.border.opacity(0.75), lineWidth: 1)
        )
    }

    private var inspectorHeader: some View {
        HStack {
            Text("Inspector")
                .maText(.headline)
            Spacer()
            Text(mode == .analyze ? "Analyze" : "Results")
                .maBadge(.info)
        }
    }

    private func section<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text(title)
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
            content()
        }
    }

    private func color(for status: String) -> Color {
        switch status.lowercased() {
        case "done": return MAStyle.ColorToken.success
        case "running", "processing": return MAStyle.ColorToken.warning
        default: return MAStyle.ColorToken.muted
        }
    }
}
