import SwiftUI
import MAStyle

struct TrackHeaderView: View {
    var title: String
    var badgeText: String

    var body: some View {
        HStack {
            Text(title)
                .maText(.headline)
            Spacer()
            Text(badgeText)
                .maChip(style: .solid, color: MAStyle.ColorToken.info)
        }
        .maCard()
    }
}
