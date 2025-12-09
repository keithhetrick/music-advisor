import SwiftUI
import MAStyle

struct SettingsView: View {
    @Binding var useDarkTheme: Bool
    var statusText: String

    var body: some View {
        HStack {
            HStack(spacing: MAStyle.Spacing.sm) {
                Text("Theme")
                    .maText(.caption)
                Toggle("", isOn: $useDarkTheme)
                    .maToggleStyle()
                    .labelsHidden()
            }
            Spacer()
            if !statusText.isEmpty {
                Text(statusText)
                    .maBadge(.info)
            }
        }
        .maCard(padding: MAStyle.Spacing.sm)
    }
}
