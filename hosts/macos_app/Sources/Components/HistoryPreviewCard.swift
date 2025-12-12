import SwiftUI
import MAStyle

struct HistoryPreviewCard: View {
    let item: SidecarItem?
    let preview: HistoryPreview?
    let onReveal: () -> Void
    let onPreview: () -> Void
    let onRerun: () -> Void
    let onViewEcho: (() -> Void)?

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            HStack {
                Text(item?.name ?? "No selection")
                    .maText(.headline)
                Spacer()
                if let preview, preview.richFound {
                    Text("Rich found").maBadge(.success)
                } else {
                    Text("Rich missing").maBadge(.warning)
                }
            }
            if let path = item?.path {
                Text(path)
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
                    .lineLimit(2)
            }
            HStack(spacing: MAStyle.Spacing.sm) {
                Button("Preview") { onPreview() }
                    .maButton(.ghost)
                    .accessibilityLabel("Preview sidecar")
                Button("Reveal") { onReveal() }
                    .maButton(.ghost)
                    .accessibilityLabel("Reveal in Finder")
                Button("Re-run") { onRerun() }
                    .maButton(.secondary)
                    .accessibilityLabel("Re-run this job")
                if onViewEcho != nil {
                    Button("View Echo") { onViewEcho?() }
                        .maButton(.ghost)
                        .accessibilityLabel("View Historical Echo")
                }
            }
            if let sidecar = preview?.sidecar {
                codeBlock(title: "Sidecar JSON", text: sidecar)
            }
            if let rich = preview?.rich {
                codeBlock(title: "Client Rich", text: rich.isEmpty ? "(missing)" : rich)
            }
            if let richPath = preview?.richPath {
                Text("Rich path: \(richPath)")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }
        }
        .maCard()
        .maGlass()
    }

    private func codeBlock(title: String, text: String) -> some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text(title).maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
            ScrollView {
                Text(text)
                    .font(MAStyle.Typography.bodyMono)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(MAStyle.Spacing.sm)
                    .background(MAStyle.ColorToken.panel.opacity(0.5))
                    .cornerRadius(MAStyle.Radius.sm)
            }
            .frame(minHeight: 80)
        }
    }
}
