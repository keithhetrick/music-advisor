import XCTest
@testable import ContentAddressedBroker

final class ContentAddressedBrokerTests: XCTestCase {
    // A URLProtocol stub to intercept requests.
    class StubProtocol: URLProtocol {
        static var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

        override class func canInit(with request: URLRequest) -> Bool { true }
        override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
        override func startLoading() {
            guard let handler = StubProtocol.handler else {
                client?.urlProtocol(self, didFailWithError: NSError(domain: "no-handler", code: -1))
                return
            }
            do {
                let (response, data) = try handler(request)
                client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
                client?.urlProtocol(self, didLoad: data)
                client?.urlProtocolDidFinishLoading(self)
            } catch {
                client?.urlProtocol(self, didFailWithError: error)
            }
        }
        override func stopLoading() {}
    }

    private func makeSession() -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [StubProtocol.self]
        return URLSession(configuration: config)
    }

    func testSubmitAndFetchJob() async throws {
        let session = makeSession()
        let client = ContentAddressedBroker(
            config: .init(baseURL: URL(string: "http://localhost:8099")!),
            session: session
        )

        // Submit mock
        StubProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/echo/jobs")
            let payload = """
            {"job_id":"abc","status":"pending"}
            """.data(using: .utf8)!
            let resp = HTTPURLResponse(url: request.url!, statusCode: 202, httpVersion: nil, headerFields: nil)!
            return (resp, payload)
        }
        let submit = try await client.submitJob(featuresPath: URL(fileURLWithPath: "/tmp/foo"))
        XCTAssertEqual(submit.jobId, "abc")

        // Status mock
        StubProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/echo/jobs/abc")
            let payload = """
            {"job_id":"abc","status":"done","result":{"artifact_path":"/echo/a/b/art.json","manifest_path":"/echo/a/b/manifest.json"}}
            """.data(using: .utf8)!
            let resp = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
            return (resp, payload)
        }
        let status = try await client.fetchJob(jobId: "abc")
        XCTAssertEqual(status.status, "done")
        XCTAssertEqual(status.result?.artifactPath, "/echo/a/b/art.json")
    }

    func testFetchArtifactEtag() async throws {
        let session = makeSession()
        let client = ContentAddressedBroker(
            config: .init(baseURL: URL(string: "http://localhost:8099")!, artifactName: "foo.json"),
            session: session
        )

        StubProtocol.handler = { request in
            XCTAssertEqual(request.value(forHTTPHeaderField: "If-None-Match"), "abc")
            let resp = HTTPURLResponse(url: request.url!, statusCode: 304, httpVersion: nil, headerFields: ["ETag": "abc"])!
            return (resp, Data())
        }
        await XCTAssertThrowsErrorAsync(try await client.fetchArtifact(configHash: "cfg", sourceHash: "src", etag: "abc")) { error in
            guard case .notModified = error as? ContentAddressedBroker.BrokerError else {
                return XCTFail("expected notModified")
            }
        }
    }

    func testFetchIndexAndArtifact200() async throws {
        let session = makeSession()
        let client = ContentAddressedBroker(
            config: .init(baseURL: URL(string: "http://localhost:8099")!),
            session: session
        )

        // Index then artifact responses.
        StubProtocol.handler = { request in
            let path = request.url?.path ?? ""
            if path.contains("/echo/index/") {
                let payload = """
                {"track_id":"foo","config_hash":"cfg","source_hash":"src","artifact":"/echo/cfg/src/historical_echo.json","manifest":"/echo/cfg/src/manifest.json","etag":"etag123"}
                """.data(using: .utf8)!
                let resp = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                return (resp, payload)
            } else if path.contains("/echo/cfg/src/historical_echo.json") {
                let resp = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: ["ETag": "etag123"])!
                return (resp, Data("artifact-body".utf8))
            }
            let resp = HTTPURLResponse(url: request.url!, statusCode: 404, httpVersion: nil, headerFields: nil)!
            return (resp, Data())
        }

        let idx = try await client.fetchLatest(trackId: "foo")
        XCTAssertEqual(idx.configHash, "cfg")
        XCTAssertEqual(idx.sourceHash, "src")
        XCTAssertEqual(idx.etag, "etag123")

        let (data, etag) = try await client.fetchArtifact(configHash: idx.configHash, sourceHash: idx.sourceHash, etag: idx.etag)
        XCTAssertEqual(data, Data("artifact-body".utf8))
        XCTAssertEqual(etag, "etag123")
    }
}

extension XCTestCase {
    func XCTAssertThrowsErrorAsync<T>(_ expression: @autoclosure () async throws -> T, _ message: @autoclosure () -> String = "", file: StaticString = #file, line: UInt = #line, _ errorHandler: (Error) -> Void = { _ in }) async {
        do {
            _ = try await expression()
            XCTFail(message(), file: file, line: line)
        } catch {
            errorHandler(error)
        }
    }
}
