import Foundation

actor RunnerService {
    private let runner = CommandRunner()

    func run(command: [String], workingDirectory: String?, extraEnv: [String: String]) -> CommandResult {
        return runner.run(command: command, workingDirectory: workingDirectory, extraEnv: extraEnv)
    }
}
