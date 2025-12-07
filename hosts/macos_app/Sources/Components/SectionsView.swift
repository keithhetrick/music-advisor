import SwiftUI
import MAStyle

struct SectionsView: View {
    var sections: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            ForEach(sections, id: \.self) { section in
                HStack {
                    Text(section)
                        .maText(.body)
                    Spacer()
                }
                .maCard(padding: MAStyle.Spacing.sm)
            }
        }
    }
}
