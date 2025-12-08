import SwiftUI
import MAStyle

/// Minimal, macOS 12-safe peek at MAStyle tokens/components.
struct MAStyleLiteShowcase: View {
    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
            Text("MAStyle (lite)")
                .maText(.headline)
            Text("macOS 12 preview. Full showcase available on macOS 13+.").maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)

            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                Text("Buttons").maText(.headline)
                HStack {
                    Button("Primary") {}.maButton(.primary)
                    Button("Secondary") {}.maButton(.secondary)
                    Button("Ghost") {}.maButton(.ghost)
                }
            }
            .maCard()

            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                Text("Badges & Chips").maText(.headline)
                HStack {
                    Text("Info").maBadge(.info)
                    Text("Success").maBadge(.success)
                    Text("Warning").maBadge(.warning)
                    Text("Danger").maBadge(.danger)
                }
                HStack {
                    Text("Solid").maChip(style: .solid)
                    Text("Outline").maChip(style: .outline)
                }
            }
            .maCard()

            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                Text("Inputs").maText(.headline)
                TextField("Text input", text: .constant(""))
                    .maInput()
                TextEditor(text: .constant("Multiline text"))
                    .frame(height: 80)
                    .maTextArea()
            }
            .maCard()

            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                Text("Progress").maText(.headline)
                ProgressView(value: 0.65)
                    .maProgressStyle()
                Text("67%")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }
            .maCard()
        }
    }
}
