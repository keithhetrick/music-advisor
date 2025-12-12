import SwiftUI
import MAStyle
import MAQueue

struct JobQueueView: View {
    var jobs: [Job]
    var expandFoldersSignal: NotificationCenter.Publisher = NotificationCenter.default.publisher(for: .uiTestExpandFolders)
    var isEnqueuing: Bool = false
    var ingestPendingCount: Int = 0
    var ingestErrorCount: Int = 0
    var onReveal: (String) -> Void
    var onPreviewRich: (String) -> Void
    var onClear: () -> Void
    var onStart: (() -> Void)? = nil
    var onStop: (() -> Void)? = nil
    var onRemove: ((UUID) -> Void)? = nil
    var onCancelPending: (() -> Void)? = nil
    var onClearCompleted: (() -> Void)? = nil
    var onClearCanceledFailed: (() -> Void)? = nil
    var onResumeCanceled: (() -> Void)? = nil
    @State private var isExpanded: Bool = true
    @State private var confirmAction: ClearAction? = nil
    @State private var showConfirm: Bool = false
    @State private var expandAllToken: Int = 0

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            header
            ingestBadgeRow
            if isExpanded {
                queueContent
            }
        }
        .maCard()
        .accessibilityIdentifier("queue-card")
        .confirmationDialog("Are you sure?", isPresented: $showConfirm) {
            if let action = confirmAction {
                switch action {
                case .all:
                    Button("Clear all", role: .destructive) { onClear() }
                case .completed:
                    Button("Clear completed", role: .destructive) { onClearCompleted?() }
                case .canceledFailed:
                    Button("Clear canceled/failed", role: .destructive) { onClearCanceledFailed?() }
                }
            }
            Button("Cancel", role: .cancel) { confirmAction = nil }
        } message: {
            if let action = confirmAction {
                switch action {
                case .all:
                    Text("This will remove all jobs from the queue.")
                case .completed:
                    Text("This will remove all completed jobs.")
                case .canceledFailed:
                    Text("This will remove canceled and failed jobs.")
                }
            }
        }
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
                    if let error = job.errorMessage, job.status == .failed || job.status == .canceled {
                        Text(error)
                            .maText(.caption)
                            .foregroundStyle(job.status == .failed ? MAStyle.ColorToken.danger : MAStyle.ColorToken.warning)
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
        .accessibilityIdentifier("queue-row-\(job.displayName)")
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
            let sortedJobs = value.sorted { $0.createdAt < $1.createdAt }
            return JobGroup(id: key,
                            name: value.first?.groupName ?? "Folder",
                            rootPath: value.first?.groupRootPath,
                            jobs: sortedJobs)
        }
        .sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
    }

    private func ungroupedJobs() -> [Job] {
        jobs.filter { $0.groupID == nil }
            .sorted { $0.createdAt < $1.createdAt }
    }

    private var queueContent: some View {
        let groups = groupedFolders()
        let singles = ungroupedJobs()

        return Group {
            if groups.isEmpty && singles.isEmpty {
                Text("Drop audio files to start a batch.")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
                    .accessibilityLabel("Queue empty")
                    .accessibilityIdentifier("queue-empty")
            } else {
                LazyVStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    groupSection(groups)
                    singleSection(singles)
                }
                .id("queue-tree-\(expandAllToken)")
                .animation(nil, value: jobs) // avoid row bouncing on frequent updates
            }
        }
        .onReceive(expandFoldersSignal) { _ in
            // No-op placeholder to trigger view update; NestedFolderTree starts expanded by default.
            isExpanded = true
            expandAllToken &+= 1
        }
    }

    @ViewBuilder
    private func groupSection(_ groups: [JobGroup]) -> some View {
        ForEach(groups, id: \.id) { group in
            // Deduplicate by path with stable ordering to avoid ID collisions and row jumping.
            var seen: Set<String> = []
            let uniqueJobs = group.jobs.filter { job in
                let path = job.fileURL.path
                if seen.contains(path) { return false }
                seen.insert(path)
                return true
            }
            let items: [FolderTreeItem<Job>] = uniqueJobs.map { job in
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
    }

    @ViewBuilder
    private func singleSection(_ singles: [Job]) -> some View {
        ForEach(singles) { job in
            jobRow(job)
        }
    }

    @ViewBuilder
    private var ingestBadgeRow: some View {
        if ingestPendingCount > 0 || ingestErrorCount > 0 {
            HStack(spacing: MAStyle.Spacing.sm) {
                if ingestPendingCount > 0 {
                    Text("Ingest pending: \(ingestPendingCount)").maBadge(.info)
                }
                if ingestErrorCount > 0 {
                    Text("Ingest errors: \(ingestErrorCount)").maBadge(.danger)
                }
            }
        }
    }

    private var header: some View {
        HStack {
            titleSection
            Spacer()
            statusBadge
            headerButtons
        }
    }

    private var titleSection: some View {
        HStack(spacing: MAStyle.Spacing.xs) {
            Text("Batch Queue")
                .maText(.headline)
            if isEnqueuing {
                ProgressView()
                    .scaleEffect(0.7)
                Text("Loading…")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }
        }
    }

    @ViewBuilder
    private var statusBadge: some View {
        switch JobQueueView.headerStatus(for: jobs) {
        case .empty:
            Text("Empty").maBadge(.neutral)
        case .processing:
            Text("Processing").maBadge(.info)
        case .queued:
            Text("Queued").maBadge(.warning)
        case .failed:
            Text("Failed").maBadge(.danger)
        case .canceled:
            Text("Canceled").maBadge(.warning)
        case .done:
            Text("Done").maBadge(.success)
        }
    }

    private var headerButtons: some View {
        HStack(spacing: MAStyle.Spacing.xs) {
            if let onStart {
                Button("Start") { onStart() }
                    .maButton(.ghost)
                    .accessibilityIdentifier("queue-start")
            }
            if JobQueueView.shouldShowStop(onStop: onStop) {
                if let onStop {
                    Button("Stop") { onStop() }
                        .maButton(.ghost)
                        .accessibilityIdentifier("queue-stop")
                }
            }
            if JobQueueView.shouldShowCancelPending(onCancelPending: onCancelPending) {
                if let onCancelPending {
                    Button("Cancel pending") { onCancelPending() }
                        .maButton(.ghost)
                        .accessibilityIdentifier("queue-cancel-pending")
                        .accessibilityLabel("Cancel pending jobs")
                }
            }
            if let onResumeCanceled, JobQueueView.shouldShowResumeCanceled(for: jobs) {
                Button("Resume canceled") { onResumeCanceled() }
                    .maButton(.ghost)
                    .accessibilityIdentifier("queue-resume-canceled")
                    .accessibilityLabel("Resume canceled jobs")
            }
            if JobQueueView.shouldShowClearCompleted(onClearCompleted: onClearCompleted) {
                Button("Clear completed") {
                    confirmAction = .completed
                    showConfirm = true
                }
                    .maButton(.ghost)
                    .accessibilityIdentifier("queue-clear-completed")
                    .accessibilityLabel("Clear completed jobs")
            }
            if JobQueueView.shouldShowClearCanceledFailed(onClearCanceledFailed: onClearCanceledFailed) {
                Button("Clear canceled/failed") {
                    confirmAction = .canceledFailed
                    showConfirm = true
                }
                    .maButton(.ghost)
                    .accessibilityIdentifier("queue-clear-canceled-failed")
                    .accessibilityLabel("Clear canceled and failed jobs")
            }
            Button("Clear (all)") {
                confirmAction = .all
                showConfirm = true
            }
                .maButton(.ghost)
                .accessibilityIdentifier("queue-clear-all")
                .accessibilityLabel("Clear all jobs")
            Button(isExpanded ? "Hide" : "Show") {
                isExpanded.toggle()
            }
            .maButton(.ghost)
            .accessibilityIdentifier("queue-toggle-visibility")
        }
    }

    private struct JobGroup {
        let id: UUID
        let name: String
        let rootPath: String?
        let jobs: [Job]
    }

    private enum ClearAction: String, Identifiable {
        case all, completed, canceledFailed
        var id: String { rawValue }
    }
}

// MARK: - Testable helpers

extension JobQueueView {
    enum HeaderStatus {
        case empty, processing, queued, failed, canceled, done
    }

    static func headerStatus(for jobs: [Job]) -> HeaderStatus {
        if jobs.isEmpty { return .empty }
        if jobs.contains(where: { $0.status == .running }) { return .processing }
        if jobs.contains(where: { $0.status == .pending }) { return .queued }
        if jobs.contains(where: { $0.status == .failed }) { return .failed }
        if jobs.contains(where: { $0.status == .canceled }) { return .canceled }
        return .done
    }

    static func shouldShowResumeCanceled(for jobs: [Job]) -> Bool {
        jobs.contains { $0.status == .canceled }
    }

    static func shouldShowStop(onStop: (() -> Void)?) -> Bool {
        onStop != nil
    }

    static func shouldShowCancelPending(onCancelPending: (() -> Void)?) -> Bool {
        onCancelPending != nil
    }

    static func shouldShowClearCompleted(onClearCompleted: (() -> Void)?) -> Bool {
        onClearCompleted != nil
    }

    static func shouldShowClearCanceledFailed(onClearCanceledFailed: (() -> Void)?) -> Bool {
        onClearCanceledFailed != nil
    }
}
