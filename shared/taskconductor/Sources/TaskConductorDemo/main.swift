import Foundation
import TaskConductor

/// Simple demo showing two “clients” enqueuing work with separate handlers.
@main
struct Demo {
    static func main() async {
        let broker = TaskConductor(
            config: .init(
                defaultWorkingDirectory: nil,
                defaultEnvironment: [:],
                defaultTimeoutSeconds: 5,
                globalLogURL: URL(fileURLWithPath: "/tmp/taskconductor-demo.log"),
                maxConcurrentTasks: 2,
                maxQueueDepth: 32,
                retryCount: 1,
                retryDelaySeconds: 0.5,
                extraLogHandler: { print("LOG:", $0) }
            )
        )

        func enqueue(_ label: String, cmd: [String]) async {
            let descriptor = TaskDescriptor(command: cmd, workingDirectory: nil, environment: [:], timeoutSeconds: 5)
            await broker.enqueue(descriptor) { event in
                print("[\(label)] \(event)")
            }
        }

        // Client A
        await enqueue("clientA", cmd: ["/bin/echo", "hello-from-A"])

        // Client B
        await enqueue("clientB", cmd: ["/bin/echo", "hello-from-B"])

        // Simulate a failure and retry
        await enqueue("clientB", cmd: ["/usr/bin/false"])

        // Allow tasks to finish
        try? await Task.sleep(nanoseconds: 3_000_000_000)
    }
}
