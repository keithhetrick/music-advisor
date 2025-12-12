import Foundation

public actor TaskConductor {
    public struct Handle: Sendable {
        public let id: UUID
    }

    private final class ProcessBox {
        let descriptor: TaskDescriptor
        let process: Process
        let startDate: Date
        let onEvent: @Sendable (TaskEvent) -> Void
        var timeoutTask: Task<Void, Never>?
        var canceled = false
        var timedOut = false
        var attempt: Int

        init(
            descriptor: TaskDescriptor,
            process: Process,
            startDate: Date,
            attempt: Int,
            onEvent: @escaping @Sendable (TaskEvent) -> Void
        ) {
            self.descriptor = descriptor
            self.process = process
            self.startDate = startDate
            self.attempt = attempt
            self.onEvent = onEvent
        }
    }

    private struct PendingItem {
        let descriptor: TaskDescriptor
        let onEvent: @Sendable (TaskEvent) -> Void
    }

    private let config: TaskConductorConfig
    private let logger: Logger
    private var pending: [PendingItem] = []
    private var running: [UUID: ProcessBox] = [:]

    public init(config: TaskConductorConfig = .init()) {
        self.config = config
        self.logger = Logger(
            globalURL: config.globalLogURL,
            rotationBytes: config.logRotationBytes,
            lineHandler: config.logLineHandler,
            extraHandler: config.extraLogHandler
        )
    }

    /// Enqueue a task. If concurrency slots are free it will start immediately, otherwise it will
    /// queue until a slot opens. If `maxQueueDepth` is exceeded, an internalError event is emitted
    /// and the task is not queued.
    @discardableResult
    public func enqueue(
        _ descriptor: TaskDescriptor,
        onEvent: @escaping @Sendable (TaskEvent) -> Void
    ) async -> Handle {
        let id = descriptor.id
        guard !descriptor.command.isEmpty else {
            emit(.internalError(id: id, message: "Empty command"), perTaskLog: descriptor.perTaskLogURL, onEvent: onEvent)
            return Handle(id: id)
        }

        if let depth = config.maxQueueDepth, pending.count >= depth {
            emit(.internalError(id: id, message: "Queue full (\(depth))"), perTaskLog: descriptor.perTaskLogURL, onEvent: onEvent)
            return Handle(id: id)
        }

        pending.append(PendingItem(descriptor: descriptor, onEvent: onEvent))
        await startNextIfPossible()
        return Handle(id: id)
    }

    /// Attempt to cancel a running task.
    public func cancel(id: UUID, onEvent: @escaping @Sendable (TaskEvent) -> Void) async {
        guard let box = running[id] else { return }
        box.canceled = true
        box.timeoutTask?.cancel()
        box.process.terminate()
        // terminationHandler will emit the event.
    }

    private func startNextIfPossible() async {
        while running.count < config.maxConcurrentTasks {
            guard !pending.isEmpty else { break }
            let next = pending.removeFirst()
            await start(item: next, attempt: 0)
        }
    }

    private func start(
        item: PendingItem,
        attempt: Int
    ) async {
        let descriptor = item.descriptor
        let onEvent = item.onEvent
        let id = descriptor.id
        let process = Process()
        let executable = descriptor.command[0]
        process.executableURL = URL(fileURLWithPath: executable)
        if descriptor.command.count > 1 {
            process.arguments = Array(descriptor.command.dropFirst())
        }

        if let workdir = descriptor.workingDirectory ?? config.defaultWorkingDirectory {
            process.currentDirectoryURL = URL(fileURLWithPath: workdir)
        }

        var env = ProcessInfo.processInfo.environment
        config.defaultEnvironment.forEach { env[$0.key] = $0.value }
        descriptor.environment.forEach { env[$0.key] = $0.value }
        process.environment = env

        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        let startDate = Date()
        let box = ProcessBox(descriptor: descriptor, process: process, startDate: startDate, attempt: attempt, onEvent: onEvent)
        running[id] = box

        hook(pipe: stdoutPipe, id: id, isStdErr: false, perTaskLog: descriptor.perTaskLogURL, onEvent: onEvent)
        hook(pipe: stderrPipe, id: id, isStdErr: true, perTaskLog: descriptor.perTaskLogURL, onEvent: onEvent)

        process.terminationHandler = { [weak self] _ in
            guard let self else { return }
            Task {
                await self.handleTermination(of: id, box: box, onEvent: onEvent)
            }
        }

        do {
            let event = TaskEvent.started(id: id, command: descriptor.command, workdir: descriptor.workingDirectory ?? config.defaultWorkingDirectory)
            emit(event, perTaskLog: descriptor.perTaskLogURL, onEvent: onEvent)
            try process.run()
        } catch {
            emit(.internalError(id: id, message: "Failed to start: \(error)"), perTaskLog: descriptor.perTaskLogURL, onEvent: onEvent)
            running[id] = nil
            await startNextIfPossible()
            return
        }

        if let timeout = descriptor.timeoutSeconds ?? config.defaultTimeoutSeconds {
            box.timeoutTask = Task { [weak self] in
                try? await Task.sleep(nanoseconds: UInt64(timeout * 1_000_000_000))
                await self?.timeout(id: id, onEvent: onEvent)
            }
        }
    }

    private func timeout(id: UUID, onEvent: @escaping @Sendable (TaskEvent) -> Void) async {
        guard let box = running[id] else { return }
        box.timedOut = true
        box.process.terminate()
        // terminationHandler will emit the event.
    }

    private func handleTermination(
        of id: UUID,
        box: ProcessBox,
        onEvent: @escaping @Sendable (TaskEvent) -> Void
    ) async {
        running[id] = nil
        box.timeoutTask?.cancel()

        let duration = Date().timeIntervalSince(box.startDate)
        let exitCode = box.process.terminationStatus

        // retry logic
        if (box.timedOut || exitCode != 0),
           box.attempt < config.retryCount {
            let nextAttempt = box.attempt + 1
            let jitter = config.retryJitterSeconds
            let base = config.retryDelaySeconds
            let delta = jitter > 0 ? Double.random(in: -jitter...jitter) : 0
            let delay = max(0, base + delta)
            emit(.retrying(id: id, attempt: nextAttempt, delay: delay), perTaskLog: box.descriptor.perTaskLogURL, onEvent: onEvent)
            Task {
                if delay > 0 {
                    try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                }
                let item = PendingItem(descriptor: box.descriptor, onEvent: box.onEvent)
                await self.start(item: item, attempt: nextAttempt)
            }
            return
        }

        let event: TaskEvent
        if box.timedOut {
            event = .timeout(id: id, duration: duration)
        } else if box.canceled {
            event = .canceled(id: id, duration: duration)
        } else if exitCode == 0 {
            event = .finished(id: id, exitCode: exitCode, duration: duration)
        } else {
            event = .failed(id: id, exitCode: exitCode, duration: duration)
        }

        emit(event, perTaskLog: box.descriptor.perTaskLogURL, onEvent: onEvent)
        await startNextIfPossible()
    }

    private func emit(
        _ event: TaskEvent,
        perTaskLog: URL?,
        onEvent: @escaping @Sendable (TaskEvent) -> Void
    ) {
        logger.log(event: event, perTaskURL: perTaskLog)
        onEvent(event)
    }

    private func hook(
        pipe: Pipe,
        id: UUID,
        isStdErr: Bool,
        perTaskLog: URL?,
        onEvent: @escaping @Sendable (TaskEvent) -> Void
    ) {
        let handle = pipe.fileHandleForReading
        final class StreamState {
            var buffer = Data()
            let queue = DispatchQueue(label: "taskconductor.stream.\(UUID().uuidString)")
        }
        let state = StreamState()

        handle.readabilityHandler = { [weak self] file in
            let data = file.availableData
            state.queue.async { [weak self] in
                    if data.isEmpty {
                        if !state.buffer.isEmpty, let line = String(data: state.buffer, encoding: .utf8) {
                            let event: TaskEvent = isStdErr ? .stderr(id: id, line: line) : .stdout(id: id, line: line)
                            if let strongSelf = self {
                                Task { await strongSelf.emit(event, perTaskLog: perTaskLog, onEvent: onEvent) }
                            }
                            state.buffer.removeAll()
                        }
                        file.readabilityHandler = nil
                        return
                    }

                state.buffer.append(data)
                // Use firstIndex(of:) for newline scanning to remain compatible with macOS 11 Foundation.
                    while let newlineIndex = state.buffer.firstIndex(of: 0x0A) { // newline byte
                        let lineData = state.buffer.subdata(in: state.buffer.startIndex..<newlineIndex)
                        state.buffer.removeSubrange(state.buffer.startIndex...newlineIndex)
                        if let line = String(data: lineData, encoding: .utf8) {
                            let event: TaskEvent = isStdErr ? .stderr(id: id, line: line) : .stdout(id: id, line: line)
                            if let strongSelf = self {
                                Task { await strongSelf.emit(event, perTaskLog: perTaskLog, onEvent: onEvent) }
                            }
                        }
                    }
            }
        }
    }
}
