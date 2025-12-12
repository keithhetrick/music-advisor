import XCTest
@testable import MusicAdvisorMacApp
@testable import MAQueue

final class JobsBuilderTests: XCTestCase {
    func testFiltersNonAudioFiles() {
        let audio = URL(fileURLWithPath: "/tmp/song.wav")
        let text = URL(fileURLWithPath: "/tmp/readme.txt")
        let pdf = URL(fileURLWithPath: "/tmp/doc.pdf")

        let entries = [audio, text, pdf].map { DropEntry(url: $0, groupID: nil, groupName: nil, groupRoot: nil) }
        let jobs = JobsBuilder.makeJobs(from: entries, baseCommand: "engine --audio placeholder --out out.json")

        XCTAssertEqual(jobs.count, 1)
        XCTAssertEqual(jobs.first?.fileURL, audio)
    }

    func testMixedAudioKeepsOrderAndSkipsJunk() {
        let urls = [
            URL(fileURLWithPath: "/tmp/a.wav"),
            URL(fileURLWithPath: "/tmp/notes.rtf"),
            URL(fileURLWithPath: "/tmp/b.flac"),
            URL(fileURLWithPath: "/tmp/thumbs.db"),
            URL(fileURLWithPath: "/tmp/c.aiff")
        ]

        let entries = urls.map { DropEntry(url: $0, groupID: nil, groupName: nil, groupRoot: nil) }
        let jobs = JobsBuilder.makeJobs(from: entries, baseCommand: "cli --audio placeholder --out out.json")

        XCTAssertEqual(jobs.map { $0.fileURL.lastPathComponent }, ["a.wav", "b.flac", "c.aiff"])
    }
}
