# ContentAddressedBroker (Swift)

Swift client for the content-addressed broker (TaskConductor-style). It handles job submit/status, latest index lookup, and artifact fetching with ETag support. Artifact/manifest filenames are configurable so the client can be used with any runner; defaults match Historical Echo.

## Add to your project

```swift
// In Package.swift
.package(path: "shared/content_addressed_broker_swift"), // local

// Or, if published, use .package(url: "...", from: "0.1.0")
```

```swift
import ContentAddressedBroker
```

## Basics

```swift
let client = ContentAddressedBroker(
    config: .init(
        baseURL: URL(string: "http://127.0.0.1:8099")!,
        timeout: 15,
        artifactName: "historical_echo.json",
        manifestName: "manifest.json"
    )
)

// Submit
let submit = try await client.submitJob(
    featuresPath: URL(fileURLWithPath: "/tmp/foo.features.json"),
    trackId: "foo"
)

// Poll
let status = try await client.fetchJob(jobId: submit.jobId)

// Fetch index pointer
let index = try await client.fetchLatest(trackId: "foo")

// Fetch artifact (ETag-aware)
let (data, etag) = try await client.fetchArtifact(
    configHash: index.configHash,
    sourceHash: index.sourceHash,
    etag: index.etag
)
```

## What it does

- Builds the broker URLs for submit/status/index/artifact.
- Handles JSON encoding/decoding for submit, status, and index.
- Supports `If-None-Match` / `ETag` on artifact fetch to respect cache hits.
- Configurable artifact/manifest filenames so you can reuse with non-Echo runners.

## Testing

- Includes unit tests with URLProtocol stubs (`ContentAddressedBrokerTests`) to validate request paths, decoding, ETag handling, and index+artifact fetch.
- Run locally: `cd shared/content_addressed_broker_swift && swift test`

## Error model

- `BrokerError.httpStatus(Int)` for non-200/202 statuses.
- `BrokerError.notModified` when the broker returns 304 to an ETag fetch.
- Decode/URL errors are surfaced directly.

## Notes

- This client is transport-only; it doesn’t parse or validate the artifact payload itself.
- It mirrors the Python broker’s HTTP surface: `/echo/jobs`, `/echo/jobs/{id}`, `/echo/index/{track_id}.json`, `/echo/{cfg}/{src}/{artifact}` and `/manifest`.

## Release checklist (suggested)

- Tag the repo (e.g., `v0.1.0`); SPM resolves versions by git tags.
- Run `swift test` in this package (or from the workspace) before tagging.
- If embedding via a git URL, update dependent manifests to the new tag.
