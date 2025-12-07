import SwiftUI
import MAStyle

struct JobQueueView: View {
    var jobs: [Job]
    var onReveal: (String) -> Void
    var onPreviewRich: (String) -> Void
    var onClear: () -> Void
    @State private var isExpanded: Bool = true

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            HStack {
                Text("Batch Queue")
                    .maText(.headline)
                Spacer()
                if jobs.isEmpty {
                    Text("Empty").maBadge(.neutral)
                } else if jobs.contains(where: { $0.status == .running }) {
                    Text("Processing").maBadge(.info)
                } else if jobs.contains(where: { $0.status == .pending }) {
                    Text("Queued").maBadge(.warning)
                } else {
                    Text("Done").maBadge(.success)
                }
                Button("Clear") { onClear() }
                    .maButton(.ghost)
                Button(isExpanded ? "Hide" : "Show") {
                    isExpanded.toggle()
                }
                .maButton(.ghost)
            }

            if isExpanded {
                if jobs.isEmpty {
                    Text("Drop audio files to start a batch.")
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                } else {
                    ForEach(jobs) { job in
                        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                            HStack {
                                VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                                    Text(job.displayName).maText(.body)
                                    Text(job.fileURL.path)
                                        .maText(.caption)
                                        .foregroundStyle(MAStyle.ColorToken.muted)
                                        .lineLimit(1)
                                }
                                Spacer()
                                statusChip(job.status)
                                if let sidecar = job.sidecarPath {
                                    Button("Reveal") { onReveal(sidecar) }
                                        .maButton(.ghost)
                                    Button("Preview Rich") {
                                        let richPath = sidecar.replacingOccurrences(of: ".json", with: ".client.rich.txt")
                                        onPreviewRich(richPath)
                                    }
                                    .maButton(.ghost)
                                }
                            }
                        }
                        .padding(MAStyle.Spacing.xs)
                        .background(MAStyle.ColorToken.panel.opacity(0.4))
                        .cornerRadius(MAStyle.Radius.sm)
                    }
                }
            }
        }
        .maCard()
    }

    @ViewBuilder
    private func statusChip(_ status: Job.Status) -> some View {
        switch status {
        case .pending:
            Text("Pending").maBadge(.neutral)
        case .running:
            Text("Running").maBadge(.info)
        case .done:
            Text("Done").maBadge(.success)
        case .failed:
            Text("Failed").maBadge(.danger)
        }
    }
}
