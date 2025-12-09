import SwiftUI

// MARK: - StatusRow
public struct StatusRow<Actions: View>: View {
    public enum StatusStyle {
        case neutral, info, success, warning, danger
    }

    let title: String
    let subtitle: String?
    let status: StatusStyle
    let progress: Double?
    let actions: Actions

    public init(title: String,
                subtitle: String? = nil,
                status: StatusStyle,
                progress: Double? = nil,
                @ViewBuilder actions: () -> Actions) {
        self.title = title
        self.subtitle = subtitle
        self.status = status
        self.progress = progress
        self.actions = actions()
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            HStack {
                VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    Text(title).maText(.body)
                    if let subtitle {
                        Text(subtitle)
                            .maText(.caption)
                            .foregroundStyle(MAStyle.ColorToken.muted)
                    }
                }
                Spacer()
                badge(for: status)
                actions
            }
            if let progress {
                if #available(macOS 13.0, *) {
                    ProgressView(value: progress)
                        .maProgressStyle()
                } else {
                    ProgressView()
                        .maProgressStyle()
                }
            }
        }
        .maCardInteractive()
    }

    @ViewBuilder
    private func badge(for status: StatusStyle) -> some View {
        switch status {
        case .neutral: Text("Pending").maBadge(.neutral)
        case .info: Text("Running").maBadge(.info)
        case .success: Text("Done").maBadge(.success)
        case .warning: Text("Warn").maBadge(.warning)
        case .danger: Text("Failed").maBadge(.danger)
        }
    }
}
