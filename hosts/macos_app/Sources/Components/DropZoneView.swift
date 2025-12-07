import SwiftUI
import MAStyle

struct DropZoneView: View {
    var onFilesDropped: ([URL]) -> Void

    @State private var isHovering = false

    var body: some View {
        VStack(spacing: MAStyle.Spacing.sm) {
            Text("Drop audio files to batch")
                .maText(.headline)
            Text("We will process them sequentially with the selected profile.")
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
            HStack(spacing: MAStyle.Spacing.sm) {
                Image(systemName: "tray.and.arrow.down")
                    .font(.title2)
                Text("Drop here")
                    .maText(.body)
            }
            .padding()
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: MAStyle.Radius.md)
                    .stroke(isHovering ? MAStyle.ColorToken.primary : MAStyle.ColorToken.border, lineWidth: 1.5)
                    .background(
                        RoundedRectangle(cornerRadius: MAStyle.Radius.md)
                            .fill(MAStyle.ColorToken.panel.opacity(isHovering ? 0.5 : 0.3))
                    )
            )
        }
        .padding(MAStyle.Spacing.sm)
        .maCard()
        .onDrop(of: [.fileURL], isTargeted: $isHovering) { providers in
            var urls: [URL] = []
            let group = DispatchGroup()
            for provider in providers {
                group.enter()
                _ = provider.loadObject(ofClass: URL.self) { url, _ in
                    if let url { urls.append(url) }
                    group.leave()
                }
            }
            group.notify(queue: .main) {
                if !urls.isEmpty {
                    onFilesDropped(urls)
                }
            }
            return true
        }
    }
}
