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
                        .accessibilityLabel("Queue empty")
                } else {
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                            ForEach(jobs) { job in
                                StatusRow<AnyView>(
                                    title: job.displayName,
                                    subtitle: job.fileURL.path,
                                    status: statusStyle(job.status),
                                    progress: job.status == .running ? job.progress : nil
                                ) {
                                    AnyView(
                                        HStack(spacing: MAStyle.Spacing.xs) {
                                            if let sidecar = job.sidecarPath {
                                                Button("Reveal") { onReveal(sidecar) }
                                                    .maButton(.ghost)
                                                    .accessibilityLabel("Reveal sidecar")
                                                Button("Preview Rich") {
                                                    let richPath = sidecar.replacingOccurrences(of: ".json", with: ".client.rich.txt")
                                                    onPreviewRich(richPath)
                                                }
                                                .maButton(.ghost)
                                                .accessibilityLabel("Preview rich text")
                                            }
                                        }
                                    )
                                }
                                .maSheen(isActive: job.status == .running, duration: 3.0, highlight: Color.white.opacity(0.08))
                            }
                        }
                    }
                }
            }
        }
        .maCardInteractive()
    }

    private func statusStyle(_ status: Job.Status) -> StatusRow<AnyView>.StatusStyle {
        switch status {
        case .pending: return .neutral
        case .running: return .info
        case .done: return .success
        case .failed: return .danger
        }
    }

    private func progressLabel(for job: Job) -> String {
        let percent = Int(job.progress * 100)
        switch job.status {
        case .pending:
            return "Pending"
        case .running:
            return "\(percent)%"
        case .done:
            return "100% (done)"
        case .failed:
            return "Failed"
        }
    }
}
