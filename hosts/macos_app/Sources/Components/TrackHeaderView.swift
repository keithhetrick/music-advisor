import SwiftUI
import MAStyle

struct TrackHeaderView: View {
    var title: String
    var badgeText: String

    var body: some View {
        CardHeader(title: title, badge: badgeText)
            .maCard()
    }
}
