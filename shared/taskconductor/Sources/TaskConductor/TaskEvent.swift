import Foundation

public enum TaskEvent: Sendable, Equatable {
    case started(id: UUID, command: [String], workdir: String?)
    case stdout(id: UUID, line: String)
    case stderr(id: UUID, line: String)
    case finished(id: UUID, exitCode: Int32, duration: TimeInterval)
    case failed(id: UUID, exitCode: Int32, duration: TimeInterval)
    case canceled(id: UUID, duration: TimeInterval)
    case timeout(id: UUID, duration: TimeInterval)
    case retrying(id: UUID, attempt: Int, delay: TimeInterval)
    case internalError(id: UUID, message: String)
}
