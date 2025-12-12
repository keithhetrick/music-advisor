import Foundation

/// Transport client for the content-addressed broker (TaskConductor-style).
public struct ContentAddressedBroker {
    public struct Config {
        public let baseURL: URL
        public let timeout: TimeInterval
        public let artifactName: String
        public let manifestName: String

        public init(
            baseURL: URL,
            timeout: TimeInterval = 15,
            artifactName: String = "historical_echo.json",
            manifestName: String = "manifest.json"
        ) {
            self.baseURL = baseURL
            self.timeout = timeout
            self.artifactName = artifactName
            self.manifestName = manifestName
        }
    }

    public struct SubmitResponse: Decodable, Equatable {
        public let jobId: String
        public let status: String?

        enum CodingKeys: String, CodingKey {
            case jobId = "job_id"
            case status
        }
    }

    public struct JobResult: Decodable, Equatable {
        public let artifactPath: String?
        public let manifestPath: String?

        enum CodingKeys: String, CodingKey {
            case artifactPath = "artifact_path"
            case manifestPath = "manifest_path"
        }
    }

    public struct JobStatus: Decodable, Equatable {
        public let jobId: String
        public let status: String
        public let error: String?
        public let result: JobResult?

        enum CodingKeys: String, CodingKey {
            case jobId = "job_id"
            case status
            case error
            case result
        }
    }

    public struct IndexPointer: Decodable, Equatable {
        public let trackId: String
        public let configHash: String
        public let sourceHash: String
        public let artifact: String
        public let manifest: String
        public let etag: String?

        enum CodingKeys: String, CodingKey {
            case trackId = "track_id"
            case configHash = "config_hash"
            case sourceHash = "source_hash"
            case artifact
            case manifest
            case etag
        }
    }

    public enum BrokerError: Error, Equatable {
        case httpStatus(Int)
        case notModified
    }

    private let config: Config
    private let session: URLSession

    public init(config: Config, session: URLSession = .shared) {
        self.config = config
        self.session = session
    }

    /// Submit a job to the broker. Returns the job id + status (pending).
    public func submitJob(
        featuresPath: URL,
        trackId: String? = nil,
        probe: [String: Any] = [:],
        dbPath: URL? = nil,
        configHash: String? = nil,
        runId: String? = nil,
        runnerOptions: [String: Any] = [:]
    ) async throws -> SubmitResponse {
        var request = URLRequest(url: config.baseURL.appendingPathComponent("echo/jobs"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = config.timeout

        var payload: [String: Any] = [
            "features_path": featuresPath.path
        ]
        if let trackId { payload["track_id"] = trackId }
        if let dbPath { payload["db_path"] = dbPath.path }
        if let configHash { payload["config_hash"] = configHash }
        if let runId { payload["run_id"] = runId }
        if !probe.isEmpty { payload["probe"] = probe }
        if !runnerOptions.isEmpty { payload["runner_kwargs"] = runnerOptions }

        request.httpBody = try JSONSerialization.data(withJSONObject: payload, options: [])

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 202 else {
            throw BrokerError.httpStatus((response as? HTTPURLResponse)?.statusCode ?? -1)
        }
        return try JSONDecoder().decode(SubmitResponse.self, from: data)
    }

    /// Poll job status; returns status + result paths if done.
    public func fetchJob(jobId: String) async throws -> JobStatus {
        let url = config.baseURL.appendingPathComponent("echo/jobs/\(jobId)")
        var request = URLRequest(url: url)
        request.timeoutInterval = config.timeout
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BrokerError.httpStatus((response as? HTTPURLResponse)?.statusCode ?? -1)
        }
        return try JSONDecoder().decode(JobStatus.self, from: data)
    }

    /// Fetch the latest pointer for a track_id (if index exists).
    public func fetchLatest(trackId: String) async throws -> IndexPointer {
        let url = config.baseURL.appendingPathComponent("echo/index/\(trackId).json")
        var request = URLRequest(url: url)
        request.timeoutInterval = config.timeout
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BrokerError.httpStatus((response as? HTTPURLResponse)?.statusCode ?? -1)
        }
        return try JSONDecoder().decode(IndexPointer.self, from: data)
    }

    /// Fetch an artifact; returns bytes + optional ETag from the response.
    public func fetchArtifact(configHash: String, sourceHash: String, etag: String? = nil) async throws -> (data: Data, etag: String?) {
        let url = config.baseURL.appendingPathComponent("echo/\(configHash)/\(sourceHash)/\(config.artifactName)")
        var request = URLRequest(url: url)
        request.timeoutInterval = config.timeout
        if let etag {
            request.setValue(etag, forHTTPHeaderField: "If-None-Match")
        }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw BrokerError.httpStatus(-1)
        }
        if http.statusCode == 304 {
            throw BrokerError.notModified
        }
        guard http.statusCode == 200 else {
            throw BrokerError.httpStatus(http.statusCode)
        }
        let etagValue = http.value(forHTTPHeaderField: "ETag")
        return (data, etagValue)
    }
}
