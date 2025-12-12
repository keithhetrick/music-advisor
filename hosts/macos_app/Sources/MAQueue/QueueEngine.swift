import Foundation
import Combine

public protocol QueueRunner {
    func run(job: Job) async -> QueueRunResult
}

public protocol QueueRunnerCancelable {
    func cancelRunning() async
}

public struct QueueRunResult {
    public let exitCode: Int32
    public let stdout: String
    public let stderr: String
    public let spawnError: String?

    public init(exitCode: Int32, stdout: String, stderr: String, spawnError: String? = nil) {
        self.exitCode = exitCode
        self.stdout = stdout
        self.stderr = stderr
        self.spawnError = spawnError
    }
}

public protocol SidecarResolver {
    func ensureSidecar(for job: Job) -> (final: String, temp: String)
    func cleanupTemp(path: String?)
    func finalize(tempPath: String?, finalPath: String?)
}

@MainActor
public final class QueueEngine: ObservableObject {
    @Published public private(set) var jobs: [Job] = []
    @Published public private(set) var ingestPendingCount: Int = 0
    @Published public private(set) var ingestErrorCount: Int = 0

    public var jobsPublisher: Published<[Job]>.Publisher { $jobs }

    private let jobVM = JobQueueViewModel()
    private let persistence: QueuePersistence
    private let outbox: IngestOutbox
    private let processor: IngestProcessor
    private let runner: QueueRunner
    private let resolver: SidecarResolver
    private var ingestedJobIDs: Set<UUID> = []
    private var tempPaths: [UUID: String] = [:]

    private var stopAfterCurrent = false
    private var currentJobID: UUID?
    private var cancellables = Set<AnyCancellable>()

    public init(runner: QueueRunner,
                ingestor: IngestSink,
                resolver: SidecarResolver,
                persistence: QueuePersistence = QueuePersistence(),
                outbox: IngestOutbox = IngestOutbox(),
                metricsHook: (() -> Void)? = nil) {
        self.runner = runner
        self.persistence = persistence
        self.outbox = outbox
        self.resolver = resolver
        self.processor = IngestProcessor(outbox: outbox, sink: ingestor, onMetrics: metricsHook)

        jobVM.jobsPublisher
            .sink { [weak self] jobs in
                self?.jobs = jobs
                self?.persistence.save(jobs)
            }
            .store(in: &cancellables)

        let loaded = persistence.load()
        if !loaded.isEmpty {
            jobVM.replaceAll(loaded)
            jobs = loaded
        }
        Task { [weak self] in await self?.refreshOutboxCounts() }
        processor.kick()
    }

    public func enqueue(_ newJobs: [Job]) {
        jobVM.addPrecomputed(newJobs)
    }

    public var viewModel: JobQueueViewModel {
        jobVM
    }

    public func start() {
        stopAfterCurrent = false
        processNext()
    }

    public func stop() {
        stopAfterCurrent = true
        jobVM.cancelPending()
        if let current = currentJobID {
            jobVM.cancelJob(jobID: current)
            if let temp = tempPaths.removeValue(forKey: current) {
                resolver.cleanupTemp(path: temp)
            }
            // Free the slot immediately even if the runner never returns
            currentJobID = nil
        }
        if let cancelable = runner as? QueueRunnerCancelable {
            Task { await cancelable.cancelRunning() }
        }
    }

    public func resumeCanceled() {
        jobVM.resumeCanceled()
    }

    public func clearAll() {
        jobVM.clear()
        currentJobID = nil
        ingestedJobIDs.removeAll()
        tempPaths.removeAll()
        if let cancelable = runner as? QueueRunnerCancelable {
            Task { await cancelable.cancelRunning() }
        }
    }

    public func resetAll() {
        clearAll()
        Task {
            await outbox.reset()
            await refreshOutboxCounts()
        }
    }

    public func clearCompleted() {
        let completedIDs = jobs.filter { $0.status == .done }.map(\.id)
        ingestedJobIDs.subtract(completedIDs)
        jobVM.clearCompleted()
    }

    public func clearCanceledFailed() {
        jobVM.clearCanceledFailed()
    }

    private func processNext() {
        guard !stopAfterCurrent else { return }
        guard currentJobID == nil else { return }
        guard let next = jobs.first(where: { $0.status == .pending }) else { return }
        currentJobID = next.id

        let paths = resolver.ensureSidecar(for: next)
        tempPaths[next.id] = paths.temp
        jobVM.assignSidecar(jobID: next.id, sidecarPath: paths.final)
        jobVM.markRunning(jobID: next.id)

        Task.detached { [weak self] in
            guard let self else { return }
            let result = await self.runner.run(job: next)
            await self.handleResult(for: next.id, tempPath: paths.temp, result: result)
        }
    }

    private func handleResult(for jobID: UUID, tempPath: String?, result: QueueRunResult) async {
        await MainActor.run {
            let storedTemp = self.tempPaths.removeValue(forKey: jobID)
            let job = self.jobs.first(where: { $0.id == jobID })
            let wasCanceled = job?.status == .canceled
            if result.exitCode == 0 && !wasCanceled {
                self.resolver.finalize(tempPath: tempPath, finalPath: job?.sidecarPath)
                self.jobVM.markDone(jobID: jobID, sidecarPath: job?.sidecarPath)
                if let fileURL = job?.fileURL, !self.ingestedJobIDs.contains(jobID) {
                    self.ingestedJobIDs.insert(jobID)
                    Task {
                        await self.outbox.enqueue(fileURL: fileURL, jobID: jobID)
                        await self.refreshOutboxCounts()
                        self.processor.kick()
                    }
                }
            } else if !wasCanceled {
                self.resolver.cleanupTemp(path: tempPath)
                let err = result.spawnError ?? (!result.stderr.isEmpty ? result.stderr : "exit \(result.exitCode)")
                self.jobVM.markFailed(jobID: jobID, error: err)
            } else {
                self.resolver.cleanupTemp(path: tempPath ?? storedTemp)
            }
            self.currentJobID = nil
            self.processNext()
        }
    }

    private func refreshOutboxCounts() async {
        let snap = await outbox.snapshot()
        await MainActor.run {
            ingestPendingCount = snap.pending
            ingestErrorCount = snap.errors
        }
    }
}
