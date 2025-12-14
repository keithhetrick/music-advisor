import Foundation
import ContentAddressedBroker

// Backwards-compatible alias so the app uses the shared Swift package.
typealias EchoBrokerClient = ContentAddressedBroker
extension ContentAddressedBroker.Config {
    static func fromEnv() -> ContentAddressedBroker.Config {
        let env = ProcessInfo.processInfo.environment
        let urlString = env["MA_ECHO_BROKER_URL"] ?? "http://127.0.0.1:8099"
        let timeout = Double(env["MA_ECHO_BROKER_TIMEOUT"] ?? "") ?? 15.0
        let base = URL(string: urlString) ?? URL(string: "http://127.0.0.1:8099")!
        return .init(baseURL: base, timeout: timeout)
    }
}

extension ContentAddressedBroker.BrokerError: LocalizedError {
    public var errorDescription: String? {
        switch self {
        case .httpStatus(let code):
            return "Broker HTTP \(code)"
        case .notModified:
            return "Not modified"
        }
    }
}
