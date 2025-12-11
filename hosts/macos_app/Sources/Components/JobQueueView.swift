import SwiftUI
import MAStyle

struct JobQueueView: View {
    var jobs: [Job]
    var isEnqueuing: Bool = false
    var onReveal: (String) -> Void
    var onPreviewRich: (String) -> Void
    var onClear: () -> Void
    var onStop: (() -> Void)? = nil
    var onRemove: ((UUID) -> Void)? = nil
    var onCancelPending: (() -> Void)? = nil
    var onClearCompleted: (() -> Void)? = nil
    var onClearCanceledFailed: (() -> Void)? = nil
    @State private var isExpanded: Bool = true

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            HStack {
                Text("Batch Queue")
                    .maText(.headline)
                if isEnqueuing {
                    HStack(spacing: MAStyle.Spacing.xs) {
                        ProgressView()
                            .scaleEffect(0.7)
                        Text("Loading…")
                            .maText(.caption)
                            .foregroundStyle(MAStyle.ColorToken.muted)
                    }
                }
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
                if let onStop {
                    Button("Stop") { onStop() }
                        .maButton(.ghost)
                }
                if let onCancelPending {
                    Button("Cancel pending") { onCancelPending() }
                        .maButton(.ghost)
                }
                if let onClearCompleted {
                    Button("Clear completed") { onClearCompleted() }
                        .maButton(.ghost)
                }
                if let onClearCanceledFailed {
                    Button("Clear canceled/failed") { onClearCanceledFailed() }
                        .maButton(.ghost)
                }
                Button("Clear") { onClear() }
                    .maButton(.ghost)
                Button(isExpanded ? "Hide" : "Show") {
                    isExpanded.toggle()
                }
                .maButton(.ghost)
            }

            if isExpanded {
                let groups = groupedFolders()
                let singles = ungroupedJobs()

                if groups.isEmpty && singles.isEmpty {
                    Text("Drop audio files to start a batch.")
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                        .accessibilityLabel("Queue empty")
                } else {
                    LazyVStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                        ForEach(groups, id: \.id) { group in
                            let items = group.jobs.map { job in
                                FolderTreeItem(path: job.fileURL.path,
                                               isRunning: job.status == .running,
                                               item: job)
                            }
                            NestedFolderTree(
                                rootName: group.name,
                                rootPath: group.rootPath ?? group.name,
                                items: items
                            ) { item in
                                jobRow(item.item)
                            }
                        }
                        ForEach(singles) { job in
                            jobRow(job)
                        }
                    }
                }
            }
        }
        .maCard()
    }

    private func jobRow(_ job: Job) -> some View {
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
                    } else {
                        Text("No sidecar yet")
                            .maText(.caption)
                            .foregroundStyle(MAStyle.ColorToken.muted)
                    }
                    if let error = job.errorMessage, job.status == .failed {
                        Text(error)
                            .maText(.caption)
                            .foregroundStyle(MAStyle.ColorToken.danger)
                            .lineLimit(1)
                            .truncationMode(.tail)
                    }
                    if let onRemove, job.status != .running {
                        Button {
                            onRemove(job.id)
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(MAStyle.ColorToken.danger)
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Remove from queue")
                    }
                }
            )
        }
        .maSheen(isActive: job.status == .running, duration: 2.6, highlight: Color.white.opacity(0.05))
    }

    private func statusStyle(_ status: Job.Status) -> StatusRow<AnyView>.StatusStyle {
        switch status {
        case .pending: return .neutral
        case .running: return .info
        case .done: return .success
        case .failed: return .danger
        case .canceled: return .warning
        }
    }

    private func groupedFolders() -> [JobGroup] {
        let grouped = Dictionary(grouping: jobs.filter { $0.groupID != nil }) { $0.groupID! }
        return grouped.compactMap { key, value in
            guard !value.isEmpty else { return nil }
            let sortedJobs = value.sorted { $0.displayName.localizedCaseInsensitiveCompare($1.displayName) == .orderedAscending }
            return JobGroup(id: key,
                            name: value.first?.groupName ?? "Folder",
                            rootPath: value.first?.groupRootPath,
                            jobs: sortedJobs)
        }
        .sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
    }

    private func ungroupedJobs() -> [Job] {
        jobs.filter { $0.groupID == nil }
            .sorted { $0.displayName.localizedCaseInsensitiveCompare($1.displayName) == .orderedAscending }
    }

    private struct JobGroup {
        let id: UUID
        let name: String
        let rootPath: String?
        let jobs: [Job]
    }
}
