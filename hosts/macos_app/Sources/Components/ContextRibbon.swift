import SwiftUI
import MAStyle

struct ContextRibbon: View {
    struct Step: Identifiable {
        let id = UUID()
        let title: String
        let status: String
        let action: (() -> Void)?
    }

    let hciValue: String?
    let axes: [(String, String)]
    let nextMove: String
    let contextLabel: String
    let contextSubtitle: String
    let steps: [Step]

    var body: some View {
        HStack(alignment: .center, spacing: MAStyle.Spacing.sm) {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                Text(contextLabel).maText(.body)
                Text(contextSubtitle)
                    .maText(.caption)
                    .foregroundStyle(DesignTokens.Color.muted)
            }
            Divider().padding(.vertical, MAStyle.Spacing.xs)
            Text("Next: \(nextMove)")
                .maText(.body)
                .foregroundStyle(DesignTokens.Color.muted)
            Divider().padding(.vertical, MAStyle.Spacing.xs)
            metricStrip
            Spacer()
            stepRail
        }
        .padding(.horizontal, MAStyle.Spacing.sm)
        .padding(.vertical, MAStyle.Spacing.xs)
        .background(.thinMaterial)
        .cornerRadius(DesignTokens.Radius.lg)
        .overlay(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.lg)
                .stroke(DesignTokens.Color.border.opacity(0.6), lineWidth: 1)
        )
    }

    private var stepRail: some View {
        HStack(spacing: MAStyle.Spacing.xs) {
            ForEach(steps) { step in
                HStack(spacing: MAStyle.Spacing.xs) {
                    Circle()
                        .fill(color(for: step.status))
                        .frame(width: 6, height: 6)
                    Text(step.title)
                        .maText(.caption)
                        .foregroundStyle(color(for: step.status))
                }
                .padding(.horizontal, MAStyle.Spacing.xs)
                .padding(.vertical, MAStyle.Spacing.xs)
                .background(DesignTokens.Color.surface.opacity(0.35))
                .cornerRadius(DesignTokens.Radius.sm)
            }
            Spacer()
        }
    }

    private var metricStrip: some View {
        HStack(spacing: MAStyle.Spacing.xs) {
            if let hciValue {
                metricPill(title: "HCI", value: hciValue)
            }
            ForEach(axes.prefix(2), id: \.0) { axis in
                metricPill(title: axis.0, value: axis.1)
            }
        }
    }

    private func metricPill(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text(title)
                .maText(.caption)
                .foregroundStyle(DesignTokens.Color.muted)
            Text(value)
                .maText(.body)
        }
        .padding(.horizontal, MAStyle.Spacing.sm)
        .padding(.vertical, MAStyle.Spacing.xs)
        .background(DesignTokens.Color.surface.opacity(0.4))
        .overlay(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.sm)
                .stroke(DesignTokens.Color.border.opacity(0.6), lineWidth: 1)
        )
        .cornerRadius(DesignTokens.Radius.sm)
    }

    private func color(for status: String) -> Color {
        switch status.lowercased() {
        case "done", "ready": return DesignTokens.Color.success
        case "running", "processing": return DesignTokens.Color.warning
        case "idle", "pending": return DesignTokens.Color.muted
        default: return DesignTokens.Color.muted
        }
    }
}
