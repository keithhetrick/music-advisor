# TaskConductor

TaskConductor is an agnostic task runner/broker library packaged as a standalone SwiftPM module. It supervises command execution, emits structured events, enforces cancel/timeout, and writes per-task and global logs. It has no UI or pipeline dependencies.

## Features

- Task descriptor input (command, env, working dir, optional timeout/log target)
- Agnostic “client” model: each enqueue carries its own event handler and never reuses a prior handler (safe for multiple frontends/backends at once)
- Structured logging (global + optional per-task) with optional rotation and live mirroring
- Event callbacks (`started`, `stdout`, `stderr`, `finished`, `failed`, `canceled`, `timeout`, `retrying`, `internalError`)
- Clean process lifecycle with cancel/timeout handling + retry/backoff
- Optional retry jitter to smooth thundering-herd restarts
- Concurrency cap with queue backpressure and explicit rejection when the queue is full
- Pluggable persistence/log sinks
- Optional per-event log hook for hosts to forward logs to their own systems (metrics, ELK, etc.) or mirror raw log lines
- Designed to be embedded by any host (apps, CLIs, services); entirely UI/pipeline agnostic

## Quick start

```swift
// Add the package as a local dependency in your Package.swift:
// .package(path: "../shared/taskconductor")

import TaskConductor

let broker = TaskConductor(
    config: .init(
        defaultWorkingDirectory: "/tmp",
        defaultEnvironment: ["PYTHONPATH": "/repo"],
        defaultTimeoutSeconds: 30,
        globalLogURL: URL(fileURLWithPath: "/tmp/taskconductor.log"),
        logRotationBytes: 5_000_000,      // rotate global log at 5MB (writes .1 on rollover)
        logLineHandler: { line in          // mirror preformatted log lines to your own logger
            print("mirror: \(line)")
        },
        maxConcurrentTasks: 2,       // limit parallelism
        maxQueueDepth: 100,          // backpressure; enqueues beyond this emit .internalError
        retryCount: 1,               // number of retries on non-zero exit
        retryDelaySeconds: 1.0,      // backoff between retries
        retryJitterSeconds: 0.3,     // +/- jitter on each retry delay
        extraLogHandler: { event in  // optional mirror to host logger/metrics
            print("forward-to-host: \(event)")
        }
    )
)

let task = TaskDescriptor(
    command: ["/bin/echo", "hello"],
    workingDirectory: nil,
    environment: [:],                // merged with config.defaultEnvironment
    timeoutSeconds: 5
)
await broker.enqueue(task) { event in
    print("event: \(event)")
}
```

## Events

- `started(id:command:workdir:)`
- `stdout(id:line:)`
- `stderr(id:line:)`
- `finished(id:exitCode:duration:)`
- `failed(id:exitCode:duration:)`
- `canceled(id:duration:)`
- `timeout(id:duration:)`
- `retrying(id:attempt:exitCode:delay:)`
- `internalError(id:message:)`
- `stdout` / `stderr` lines are streamed incrementally (per-stream state avoids interleaving).

## Cancellation

`cancel(id:onEvent:)` terminates a running process. The termination handler emits `.canceled`.

## Concurrency, queue depth, and backpressure

- `maxConcurrentTasks` controls the number of in-flight processes. Waiting tasks remain pending.
- `maxQueueDepth` controls the pending queue size. If an enqueue would exceed it, the task immediately emits `.internalError` with a “queue full” message (caller can show a toast or fall back to a different lane).

## Retries

Set `retryCount > 0` to automatically retry a task that exits non-zero. Each retry emits `.retrying` with the attempt number and exit code. After the final attempt, a `.failed` event is emitted.

## Logging

- Global log (single file) controlled by `TaskConductorConfig.globalLogURL`
- Optional per-task log via `TaskDescriptor.perTaskLogURL`
- Optional mirror via `extraLogHandler` for hosts to forward events to their own system
- Optional mirror via `logLineHandler` to receive preformatted log lines (same content as the file)
- Optional rotation via `logRotationBytes` (when reached, the current log is renamed with `.1` and a new file begins)
- Each line: `ISO8601 timestamp` + event description

## Multi-client isolation

Each queued item carries its own event handler and state, so two distinct callers (e.g., UI queue + headless ingest) cannot see cross-talk. Retries reuse the correct per-item handler so callbacks never leak between clients.

## Tests

```bash
# From repo root; caches keep builds fast and isolated
mkdir -p .home .swiftpm-cache .swiftpm-module-cache .swiftpm-clang-module-cache
HOME=$PWD/.home \
SWIFTPM_CACHE_PATH=$PWD/.swiftpm-cache \
SWIFT_MODULE_CACHE_PATH=$PWD/.swiftpm-module-cache \
CLANG_MODULE_CACHE_PATH=$PWD/.swiftpm-clang-module-cache \
swift test --package-path shared/taskconductor --disable-sandbox \
  -Xcc -fmodules-cache-path="$PWD/.swiftpm-clang-module-cache" \
  -Xswiftc -module-cache-path -Xswiftc "$PWD/.swiftpm-module-cache"
```

## Demo executable

Run a tiny demo that enqueues a few tasks with two “clients”:

```bash
swift run --package-path shared/taskconductor TaskConductorDemo
```

## Recipes

- **Two clients, separate handlers:** enqueue from different callers; each PendingItem carries its own onEvent so callbacks never cross.
- **Backpressure UX:** set `maxQueueDepth` low during UI testing to confirm the caller receives `.internalError` when the queue is full.
- **Retries with delay:** set `retryCount` and `retryDelaySeconds`; watch `.retrying` events before `.failed`.
- **Retry jitter:** set `retryJitterSeconds` to smooth retry spikes (delay is randomized within base ± jitter).
- **Mirror logs to host:** provide `extraLogHandler` to forward lines to your own logger/metrics.
- **Stream logs live:** provide `logLineHandler` to receive preformatted log lines as they are written.
- **Per-task logs:** set `perTaskLogURL` in TaskDescriptor to capture stdout/stderr/termination for a single job.

## Status

Ready for embedding. Future niceties you can add:

- Rotation and pluggable log sinks
- Richer backoff policies (jitter, caps)
- More host integration examples
- A tiny example target (CLI) that enqueues a mix of tasks and prints events
