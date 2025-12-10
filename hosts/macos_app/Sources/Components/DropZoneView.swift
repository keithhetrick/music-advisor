import SwiftUI
import UniformTypeIdentifiers
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
        .maGlass()
        .accessibilityLabel("Drop zone")
        .accessibilityHint("Drop audio files to enqueue them for processing")
        .contentShape(Rectangle())
        // Legacy-compatible drop handler (macOS 12-friendly)
        .onDrop(of: [UTType.fileURL, UTType.audio, UTType.movie],
                isTargeted: $isHovering) { providers in
            var urls: [URL] = []
            let group = DispatchGroup()

            for provider in providers {
                if provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) ||
                    provider.hasItemConformingToTypeIdentifier(UTType.audio.identifier) ||
                    provider.hasItemConformingToTypeIdentifier(UTType.movie.identifier) {
                    group.enter()
                    loadURL(from: provider) { url in
                        if let url {
                            urls.append(url)
                        }
                        group.leave()
                    }
                }
            }

            group.notify(queue: .main) {
                guard !urls.isEmpty else { return }
                onFilesDropped(urls)
            }

            return true
        }
        .frame(maxWidth: .infinity)
    }

    private func loadURL(from provider: NSItemProvider, completion: @escaping (URL?) -> Void) {
        if provider.canLoadObject(ofClass: URL.self) {
            _ = provider.loadObject(ofClass: URL.self) { url, _ in
                DispatchQueue.main.async {
                    completion(url)
                }
            }
        } else {
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                DispatchQueue.main.async {
                    if let data = item as? Data {
                        completion(URL(dataRepresentation: data, relativeTo: nil))
                    } else if let url = item as? URL {
                        completion(url)
                    } else {
                        completion(nil)
                    }
                }
            }
        }
    }
}
