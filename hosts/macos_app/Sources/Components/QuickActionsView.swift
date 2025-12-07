import SwiftUI
import MAStyle

struct QuickActionsView: View {
    var actions: [(title: String, symbol: String)]

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            HStack {
                Text("Warnings")
                    .maText(.headline)
                Spacer()
            }
            HStack(spacing: MAStyle.Spacing.sm) {
                ForEach(actions, id: \.title) { action in
                    Label(action.title, systemImage: action.symbol)
                        .maChip(style: .outline, color: MAStyle.ColorToken.primary)
                }
                Spacer()
            }
        }
        .maCard()
    }
}
