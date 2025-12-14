import XCTest
@testable import ContentAddressedBroker
import Foundation
import Network

final class HttpContractTests: XCTestCase {
    func testHttpContractSubmitStatusIndexArtifact() async throws {
        // Spin up the Python broker on a random port with a dummy runner.
        // This test will be skipped if we cannot bind or execute the broker script.
        let brokerPort = try findFreePort()
        let casRoot = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: casRoot, withIntermediateDirectories: true)

        let scriptURL = URL(fileURLWithPath: "shared/content_addressed_broker/tests/test_http_contract.py")
        if !FileManager.default.fileExists(atPath: scriptURL.path) {
            throw XCTSkip("Python broker test script not found; skipping HTTP contract test")
        }

        let (process, port) = try startBroker(port: brokerPort, casRoot: casRoot)
        defer { process.terminate() }

        let client = ContentAddressedBroker(config: .init(baseURL: URL(string: "http://127.0.0.1:\(port)")!))

        // Submit a job with a fake features file
        let featuresPath = casRoot.appendingPathComponent("feat.json")
        try "{}".data(using: .utf8)?.write(to: featuresPath)
        let submit = try await client.submitJob(featuresPath: featuresPath, trackId: "foo")
        XCTAssertFalse(submit.jobId.isEmpty)

        // Poll status until done
        var status: ContentAddressedBroker.JobStatus?
        for _ in 0..<50 {
            let s = try await client.fetchJob(jobId: submit.jobId)
            if s.status == "done" {
                status = s
                break
            }
            try await Task.sleep(nanoseconds: 50_000_000)
        }
        guard let jobStatus = status else {
            XCTFail("job did not complete")
            return
        }
        XCTAssertEqual(jobStatus.status, "done")

        // Fetch index
        let idx = try await client.fetchLatest(trackId: "foo")
        XCTAssertEqual(idx.trackId, "foo")

        // Fetch artifact with ETag
        let (data, etag) = try await client.fetchArtifact(configHash: idx.configHash, sourceHash: idx.sourceHash, etag: idx.etag)
        XCTAssertFalse(data.isEmpty)
        XCTAssertEqual(etag, idx.etag)

        // If-None-Match should yield notModified
        await XCTAssertThrowsErrorAsync(try await client.fetchArtifact(configHash: idx.configHash, sourceHash: idx.sourceHash, etag: etag)) { error in
            guard case .notModified = error as? ContentAddressedBroker.BrokerError else {
                return XCTFail("expected notModified")
            }
        }
    }

    private func startBroker(port: Int, casRoot: URL) throws -> (Process, Int) {
        let brokerScript = URL(fileURLWithPath: "shared/content_addressed_broker/broker.py")
        if !FileManager.default.fileExists(atPath: brokerScript.path) {
            throw XCTSkip("Broker script not found; skipping HTTP contract test")
        }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = [
            "python3",
            brokerScript.path,
            "--cas-root", casRoot.path,
            "--port", "\(port)"
        ]
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        try process.run()

        // Wait briefly for the server to start
        try waitForPort(port)
        return (process, port)
    }

    private func findFreePort() throws -> Int {
        let listener = try NWListener(using: .tcp, on: .any)
        listener.start(queue: .global())
        let port = listener.port?.rawValue ?? 0
        listener.cancel()
        if port == 0 { throw XCTSkip("Could not allocate port") }
        return Int(port)
    }

    private func waitForPort(_ port: Int, timeout: TimeInterval = 2.0) throws {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            let conn = NWConnection(host: .ipv4(IPv4Address("127.0.0.1")!), port: NWEndpoint.Port(rawValue: UInt16(port))!, using: .tcp)
            let sem = DispatchSemaphore(value: 0)
            var reachable = false
            conn.stateUpdateHandler = { state in
                switch state {
                case .ready:
                    reachable = true
                    sem.signal()
                    conn.cancel()
                case .failed, .waiting:
                    sem.signal()
                    conn.cancel()
                default:
                    break
                }
            }
            conn.start(queue: .global())
            _ = sem.wait(timeout: .now() + 0.1)
            if reachable { return }
            Thread.sleep(forTimeInterval: 0.05)
        }
        throw XCTSkip("Broker port not reachable; skipping")
    }
}
